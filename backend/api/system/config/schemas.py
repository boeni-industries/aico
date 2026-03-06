from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


ConfigFormat = Literal["yaml", "json"]
DomainStatus = Literal["valid", "invalid", "unknown"]
Severity = Literal["error", "warning", "info"]


class DomainCard(BaseModel):
    domain: str
    display_name: str
    format: ConfigFormat
    status: DomainStatus
    last_modified: str
    source_hierarchy: List[str]
    etag: str


class DomainsResponse(BaseModel):
    domains: List[DomainCard]


class DomainConfigResponse(BaseModel):
    domain: str
    format: ConfigFormat
    content: str
    etag: str
    last_modified: str


class SchemaResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    domain: str
    schema_definition: Dict[str, Any] = Field(alias="schema")
    meta: Dict[str, Any]


class Location(BaseModel):
    start_line: int
    start_col: int
    end_line: int
    end_col: int


class ValidationIssue(BaseModel):
    path: str = ""
    message: str
    severity: Severity = "error"
    location: Optional[Location] = None


class ValidateDraftRequest(BaseModel):
    domain: str
    format: ConfigFormat
    content: str
    etag: Optional[str] = None


class ValidateDraftResponse(BaseModel):
    domain: str
    valid: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    computed: Dict[str, Any] = Field(default_factory=dict)


class SaveDomainRequest(BaseModel):
    format: ConfigFormat
    content: str
    etag: str


class SaveDomainResponse(BaseModel):
    domain: str
    saved: bool
    applied: bool
    etag: str
    last_modified: str
    result: Dict[str, Any] = Field(default_factory=dict)


class RevertDomainResponse(BaseModel):
    domain: str
    reverted: bool
    applied: bool
    etag: str
    last_modified: str
    result: Dict[str, Any] = Field(default_factory=dict)


class ReloadRequest(BaseModel):
    scope: Literal["all", "domain"]
    domain: Optional[str] = None


class ReloadDomainResult(BaseModel):
    domain: str
    status: DomainStatus
    etag: str
    last_modified: str


class ReloadResponse(BaseModel):
    reloaded: bool
    domains: List[ReloadDomainResult] = Field(default_factory=list)


class ExportResponse(BaseModel):
    scope: str
    format: ConfigFormat
    content: str


class ImportRequest(BaseModel):
    scope: Literal["all", "domain"]
    domain: Optional[str] = None
    format: ConfigFormat
    content: str
    mode: Literal["validate_only", "apply"]


class ImportResult(BaseModel):
    domain: str
    valid: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    changed_paths: List[str] = Field(default_factory=list)
    restart_required: bool = False


class ImportResponse(BaseModel):
    accepted: bool
    mode: str
    results: List[ImportResult] = Field(default_factory=list)
