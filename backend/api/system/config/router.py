from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from aico.core.config import ConfigurationManager, ConfigurationValidationError
from aico.core.logging import get_logger
from backend.api.system.dependencies import get_current_user

from . import schemas


logger = get_logger("backend.api.system.config")
router = APIRouter()


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_etag(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _domain_display_name(domain: str) -> str:
    return domain.replace("_", " ").title()


def _config_manager(request: Request) -> ConfigurationManager:
    if hasattr(request.app.state, "service_container"):
        try:
            return request.app.state.service_container.get_service("config_manager")
        except Exception:
            pass
    cfg = ConfigurationManager()
    cfg.initialize(lightweight=True)
    return cfg


def _schema_path(cfg: ConfigurationManager, domain: str) -> Path:
    return cfg.config_dir / "schemas" / f"{domain}.schema.json"


def _default_config_path(cfg: ConfigurationManager, domain: str) -> Path:
    return cfg.config_dir / "defaults" / f"{domain}.yaml"


def _user_config_path(cfg: ConfigurationManager, domain: str) -> Path:
    return cfg.user_config_dir / "user" / f"{domain}.yaml"


def _domain_exists(cfg: ConfigurationManager, domain: str) -> bool:
    return _schema_path(cfg, domain).exists() or _default_config_path(cfg, domain).exists() or domain in cfg.schemas


def _domain_has_schema(cfg: ConfigurationManager, domain: str) -> bool:
    return domain in cfg.schemas or _schema_path(cfg, domain).exists()


def _detect_domain_format(cfg: ConfigurationManager, domain: str) -> schemas.ConfigFormat:
    if _user_config_path(cfg, domain).exists():
        return "yaml"
    if _default_config_path(cfg, domain).exists():
        return "yaml"
    return "yaml"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _file_last_modified(path: Path) -> Optional[datetime]:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except FileNotFoundError:
        return None


def _current_domain_source_hierarchy(cfg: ConfigurationManager, domain: str) -> List[str]:
    hierarchy = []
    for source in cfg.sources:
        name = source.name
        if name.startswith("defaults/") and "defaults" not in hierarchy:
            hierarchy.append("defaults")
        elif name.startswith("environment/") and "env" not in hierarchy:
            hierarchy.append("env")
        elif name.startswith("user/") and "file" not in hierarchy:
            hierarchy.append("file")
        elif name == "environment_variables" and "env" not in hierarchy:
            hierarchy.append("env")
        elif name == "runtime" and "runtime_overrides" not in hierarchy:
            hierarchy.append("runtime_overrides")
    return hierarchy


def _parse_content(fmt: schemas.ConfigFormat, content: str) -> Dict[str, Any]:
    if fmt == "json":
        return json.loads(content) if content.strip() else {}
    return yaml.safe_load(content) if content.strip() else {}


def _dump_content(fmt: schemas.ConfigFormat, data: Any) -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _diff_paths(a: Any, b: Any, prefix: str = "") -> List[str]:
    changed: List[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            pa = a.get(k)
            pb = b.get(k)
            p = f"{prefix}.{k}" if prefix else k
            if isinstance(pa, dict) and isinstance(pb, dict):
                changed.extend(_diff_paths(pa, pb, p))
            else:
                if pa != pb:
                    changed.append(p)
        return changed
    if a != b and prefix:
        return [prefix]
    return changed


def _domain_etag(cfg: ConfigurationManager, domain: str) -> Tuple[str, str]:
    user_path = _user_config_path(cfg, domain)
    default_path = _default_config_path(cfg, domain)

    if user_path.exists():
        content = _read_text(user_path)
        mtime = _file_last_modified(user_path)
        lm = _rfc3339(mtime) if mtime else _rfc3339(datetime.now(timezone.utc))
        return _stable_etag("user", domain, content, lm), lm

    if default_path.exists():
        content = _read_text(default_path)
        mtime = _file_last_modified(default_path)
        lm = _rfc3339(mtime) if mtime else _rfc3339(datetime.now(timezone.utc))
        return _stable_etag("defaults", domain, content, lm), lm

    lm = _rfc3339(datetime.now(timezone.utc))
    return _stable_etag("none", domain, lm), lm


def _jsonschema_error_path(err: jsonschema.ValidationError) -> str:
    segments: List[object] = list(getattr(err, "absolute_path", []) or [])
    params = getattr(err, "params", None) or {}
    missing_prop = params.get("property")
    if missing_prop is not None:
        segments.append(missing_prop)

    if not segments:
        return ""

    out = ""
    for seg in segments:
        if isinstance(seg, int):
            out += f"[{seg}]"
            continue
        if not out:
            out = str(seg)
        else:
            out += f".{seg}"
    return out


def _best_effort_location_for_key(
    raw_content: str,
    fmt: schemas.ConfigFormat,
    key: str,
) -> Optional[schemas.Location]:
    if not key:
        return None

    if fmt == "yaml":
        pattern = re.compile(rf"^([ \t]*){re.escape(key)}\s*:\s*.*$", re.MULTILINE)
        match = pattern.search(raw_content)
        if not match:
            return None

        start_index = match.start(0)
        start_line = raw_content.count("\n", 0, start_index) + 1
        line_start = raw_content.rfind("\n", 0, start_index)
        if line_start < 0:
            line_start = 0
        else:
            line_start += 1
        start_col = (start_index - line_start) + 1
        end_col = start_col + len(key)
        return schemas.Location(
            start_line=start_line,
            start_col=start_col,
            end_line=start_line,
            end_col=end_col,
        )

    if fmt == "json":
        needle = f"\"{key}\""
        idx = raw_content.find(needle)
        if idx < 0:
            return None

        start_line = raw_content.count("\n", 0, idx) + 1
        line_start = raw_content.rfind("\n", 0, idx)
        if line_start < 0:
            line_start = 0
        else:
            line_start += 1
        start_col = (idx - line_start) + 1
        end_col = start_col + len(needle)
        return schemas.Location(
            start_line=start_line,
            start_col=start_col,
            end_line=start_line,
            end_col=end_col,
        )

    return None


def _issue_from_jsonschema_error(
    err: jsonschema.ValidationError,
    raw_content: str,
    fmt: schemas.ConfigFormat,
) -> schemas.ValidationIssue:
    path = _jsonschema_error_path(err)
    key_for_location = ""
    if path:
        key_for_location = path.split(".")[-1]
        if "[" in key_for_location:
            key_for_location = key_for_location.split("[")[0]

    location = _best_effort_location_for_key(raw_content=raw_content, fmt=fmt, key=key_for_location)
    return schemas.ValidationIssue(
        path=path,
        message=getattr(err, "message", str(err)),
        severity="error",
        location=location,
    )


@router.get("/domains", response_model=schemas.DomainsResponse)
async def list_domains(
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.DomainsResponse:
    cfg = _config_manager(request)

    domains: List[str] = []
    defaults_dir = cfg.config_dir / "defaults"
    schemas_dir = cfg.config_dir / "schemas"

    if defaults_dir.exists():
        domains.extend([p.stem for p in defaults_dir.glob("*.yaml")])
    if schemas_dir.exists():
        domains.extend([p.stem.replace(".schema", "") for p in schemas_dir.glob("*.schema.json")])
    domains = sorted(set(domains))

    result: List[schemas.DomainCard] = []
    for domain in domains:
        if not _domain_exists(cfg, domain):
            continue
        if not _domain_has_schema(cfg, domain):
            continue

        etag, last_modified = _domain_etag(cfg, domain)

        status_val: schemas.DomainStatus = "unknown"
        try:
            domain_config = cfg.config_cache.get(domain, {})
            if isinstance(domain_config, dict) and domain in cfg.schemas:
                cfg.validate(domain, domain_config)
                status_val = "valid"
        except Exception:
            status_val = "invalid"

        result.append(
            schemas.DomainCard(
                domain=domain,
                display_name=_domain_display_name(domain),
                format=_detect_domain_format(cfg, domain),
                status=status_val,
                last_modified=last_modified,
                source_hierarchy=_current_domain_source_hierarchy(cfg, domain),
                etag=etag,
            )
        )

    return schemas.DomainsResponse(domains=result)


@router.get("/domain/{domain}", response_model=schemas.DomainConfigResponse)
async def load_domain(
    domain: str,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.DomainConfigResponse:
    cfg = _config_manager(request)
    if not _domain_exists(cfg, domain):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    fmt = _detect_domain_format(cfg, domain)

    user_path = _user_config_path(cfg, domain)
    default_path = _default_config_path(cfg, domain)

    if user_path.exists():
        content = _read_text(user_path)
    elif default_path.exists():
        content = _read_text(default_path)
    else:
        domain_data = cfg.config_cache.get(domain, {}) if isinstance(cfg.config_cache.get(domain, {}), dict) else {}
        content = _dump_content(fmt, domain_data)

    etag, last_modified = _domain_etag(cfg, domain)

    return schemas.DomainConfigResponse(
        domain=domain,
        format=fmt,
        content=content,
        etag=etag,
        last_modified=last_modified,
    )


@router.get("/schema/{domain}", response_model=schemas.SchemaResponse)
async def get_domain_schema(
    domain: str,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.SchemaResponse:
    cfg = _config_manager(request)
    if not _domain_exists(cfg, domain):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    schema = cfg.schemas.get(domain)
    if not schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")

    return schemas.SchemaResponse(
        domain=domain,
        schema_definition=schema,
        meta={
            "source": "contracts",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


@router.post("/validate", response_model=schemas.ValidateDraftResponse)
async def validate_draft(
    body: schemas.ValidateDraftRequest,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.ValidateDraftResponse:
    cfg = _config_manager(request)
    domain = body.domain

    if not _domain_exists(cfg, domain):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    try:
        draft_parsed = _parse_content(body.format, body.content)
    except Exception as exc:
        return schemas.ValidateDraftResponse(
            domain=domain,
            valid=False,
            errors=[schemas.ValidationIssue(message=str(exc), severity="error")],
            computed={"changed_paths": [], "restart_required": False, "affected_services": []},
        )

    existing_effective = cfg.config_cache.get(domain, {}) if isinstance(cfg.config_cache.get(domain, {}), dict) else {}
    merged = draft_parsed

    issues: List[schemas.ValidationIssue] = []
    valid = True
    try:
        if domain in cfg.schemas:
            schema = cfg.schemas.get(domain)
            if not schema:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schema not found")
            validator = jsonschema.Draft7Validator(schema)
            errors = sorted(validator.iter_errors(merged), key=lambda e: list(e.absolute_path))
            if errors:
                valid = False
                issues.extend([
                    _issue_from_jsonschema_error(e, raw_content=body.content, fmt=body.format)
                    for e in errors
                ])
    except ConfigurationValidationError as exc:
        valid = False
        issues.append(schemas.ValidationIssue(message=str(exc), severity="error"))
    except Exception as exc:
        valid = False
        issues.append(schemas.ValidationIssue(message=str(exc), severity="error"))

    changed_paths = _diff_paths(existing_effective, merged)

    return schemas.ValidateDraftResponse(
        domain=domain,
        valid=valid,
        errors=issues,
        computed={
            "changed_paths": changed_paths,
            "restart_required": False,
            "affected_services": ["backend"],
        },
    )


@router.put("/domain/{domain}", response_model=schemas.SaveDomainResponse)
async def save_domain(
    domain: str,
    body: schemas.SaveDomainRequest,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.SaveDomainResponse:
    cfg = _config_manager(request)
    if not _domain_exists(cfg, domain):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    current_etag, _ = _domain_etag(cfg, domain)
    if body.etag != current_etag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": "Config was modified", "current_etag": current_etag},
        )

    try:
        parsed = _parse_content(body.format, body.content)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    existing_effective = cfg.config_cache.get(domain, {}) if isinstance(cfg.config_cache.get(domain, {}), dict) else {}
    merged = parsed

    try:
        if domain in cfg.schemas:
            cfg.validate(domain, merged)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    user_path = _user_config_path(cfg, domain)
    user_path.parent.mkdir(parents=True, exist_ok=True)
    user_path.write_text(body.content, encoding="utf-8")

    cfg.reload()

    new_etag, last_modified = _domain_etag(cfg, domain)
    changed_paths = _diff_paths(existing_effective, merged)

    return schemas.SaveDomainResponse(
        domain=domain,
        saved=True,
        applied=True,
        etag=new_etag,
        last_modified=last_modified,
        result={
            "changed_paths": changed_paths,
            "restart_required": False,
            "affected_services": ["backend"],
        },
    )


@router.delete("/domain/{domain}", response_model=schemas.RevertDomainResponse)
async def revert_domain_to_factory_defaults(
    domain: str,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.RevertDomainResponse:
    cfg = _config_manager(request)
    if not _domain_exists(cfg, domain):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    existing_effective = cfg.config_cache.get(domain, {}) if isinstance(cfg.config_cache.get(domain, {}), dict) else {}

    user_path = _user_config_path(cfg, domain)
    if user_path.exists():
        user_path.unlink()

    cfg.reload()

    new_effective = cfg.config_cache.get(domain, {}) if isinstance(cfg.config_cache.get(domain, {}), dict) else {}
    changed_paths = _diff_paths(existing_effective, new_effective)

    new_etag, last_modified = _domain_etag(cfg, domain)
    return schemas.RevertDomainResponse(
        domain=domain,
        reverted=True,
        applied=True,
        etag=new_etag,
        last_modified=last_modified,
        result={
            "changed_paths": changed_paths,
            "restart_required": False,
            "affected_services": ["backend"],
        },
    )


@router.post("/reload", response_model=schemas.ReloadResponse)
async def reload_from_disk(
    body: schemas.ReloadRequest,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.ReloadResponse:
    cfg = _config_manager(request)

    if body.scope == "domain":
        if not body.domain:
            raise HTTPException(status_code=400, detail="domain is required for scope=domain")
        if not _domain_exists(cfg, body.domain):
            raise HTTPException(status_code=404, detail="Domain not found")

    cfg.reload()

    domains_resp = await list_domains(request, _)
    domains: List[schemas.ReloadDomainResult] = []
    for d in domains_resp.domains:
        domains.append(
            schemas.ReloadDomainResult(
                domain=d.domain,
                status=d.status,
                etag=d.etag,
                last_modified=d.last_modified,
            )
        )

    if body.scope == "domain":
        domains = [d for d in domains if d.domain == body.domain]

    return schemas.ReloadResponse(reloaded=True, domains=domains)


@router.get("/export", response_model=schemas.ExportResponse)
async def export_config(
    request: Request,
    scope: str = Query(default="all"),
    domain: Optional[str] = Query(default=None),
    format: schemas.ConfigFormat = Query(default="yaml"),
    include_sensitive: bool = Query(default=False),
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.ExportResponse:
    cfg = _config_manager(request)

    if include_sensitive:
        raise HTTPException(status_code=403, detail="include_sensitive not supported")

    if scope == "domain":
        if not domain:
            raise HTTPException(status_code=400, detail="domain is required for scope=domain")
        if not _domain_exists(cfg, domain):
            raise HTTPException(status_code=404, detail="Domain not found")

        domain_data = cfg.config_cache.get(domain, {}) if isinstance(cfg.config_cache.get(domain, {}), dict) else {}
        return schemas.ExportResponse(
            scope="domain",
            format=format,
            content=_dump_content(format, {domain: domain_data} if scope == "domain" else domain_data),
        )

    export_data: Dict[str, Any] = {}
    for d in cfg.config_cache.keys():
        if not isinstance(cfg.config_cache.get(d), dict):
            continue
        export_data[d] = cfg.config_cache.get(d, {})

    return schemas.ExportResponse(
        scope="all",
        format=format,
        content=_dump_content(format, export_data),
    )


@router.post("/import", response_model=schemas.ImportResponse)
async def import_config(
    body: schemas.ImportRequest,
    request: Request,
    _: Dict[str, Any] = Depends(get_current_user),
) -> schemas.ImportResponse:
    cfg = _config_manager(request)

    try:
        parsed = _parse_content(body.format, body.content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    items: Dict[str, Any]
    if body.scope == "domain":
        if not body.domain:
            raise HTTPException(status_code=400, detail="domain is required for scope=domain")
        if not _domain_exists(cfg, body.domain):
            raise HTTPException(status_code=404, detail="Domain not found")
        items = {body.domain: parsed}
    else:
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=422, detail="Expected object with domain keys")
        items = parsed

    results: List[schemas.ImportResult] = []

    for d, cfg_data in items.items():
        if not _domain_exists(cfg, d):
            results.append(
                schemas.ImportResult(
                    domain=d,
                    valid=False,
                    errors=[schemas.ValidationIssue(message="Domain not found", severity="error")],
                    restart_required=False,
                )
            )
            continue

        existing_effective = cfg.config_cache.get(d, {}) if isinstance(cfg.config_cache.get(d, {}), dict) else {}
        merged = cfg_data if isinstance(cfg_data, dict) else {}

        valid = True
        issues: List[schemas.ValidationIssue] = []
        try:
            if d in cfg.schemas:
                cfg.validate(d, merged)
        except Exception as exc:
            valid = False
            issues.append(schemas.ValidationIssue(message=str(exc), severity="error"))

        changed_paths = _diff_paths(existing_effective, merged)

        if body.mode == "apply" and valid:
            user_path = _user_config_path(cfg, d)
            user_path.parent.mkdir(parents=True, exist_ok=True)
            user_path.write_text(_dump_content("yaml", merged), encoding="utf-8")

        results.append(
            schemas.ImportResult(
                domain=d,
                valid=valid,
                errors=issues,
                changed_paths=changed_paths,
                restart_required=False,
            )
        )

    if body.mode == "apply":
        cfg.reload()

    return schemas.ImportResponse(accepted=True, mode=body.mode, results=results)
