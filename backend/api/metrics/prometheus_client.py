from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx


class PrometheusQueryError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrometheusSample:
    labels: Dict[str, str]
    value: float


class PrometheusClient:
    def __init__(self, base_url: Optional[str] = None, timeout_seconds: float = 5.0) -> None:
        # NOTE:
        # - When running inside docker-compose, the Prometheus service is reachable as http://prometheus:9090
        # - When running the backend directly on the host (common during dev), Prometheus is typically exposed on
        #   localhost:9090 and the docker DNS name will not resolve.
        # Prefer explicit overrides via base_url / env var, otherwise default to localhost with a safe fallback.
        env_url = os.getenv("AICO_PROMETHEUS_URL")
        self._explicit_base_url = (base_url or env_url)
        self.base_url = (self._explicit_base_url or "http://localhost:9090").rstrip("/")
        self._timeout = timeout_seconds

    async def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        urls_to_try = [self.base_url]
        # If the user did not explicitly configure a base URL, also try the docker DNS name.
        if not self._explicit_base_url:
            urls_to_try.append("http://prometheus:9090")

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for base in urls_to_try:
                try:
                    resp = await client.get(f"{base.rstrip('/')}{path}", params=params)
                    resp.raise_for_status()
                    return resp.json()
                except Exception as exc:
                    last_exc = exc
                    continue

        raise last_exc or RuntimeError("Failed to query Prometheus")

    async def query(self, promql: str, ts: Optional[float] = None) -> List[PrometheusSample]:
        params: Dict[str, Any] = {"query": promql}
        if ts is not None:
            params["time"] = ts

        payload = await self._get_json("/api/v1/query", params=params)

        if payload.get("status") != "success":
            raise PrometheusQueryError(str(payload))

        data = payload.get("data") or {}
        result = data.get("result") or []

        samples: List[PrometheusSample] = []
        for item in result:
            metric = item.get("metric") or {}
            value_pair = item.get("value")
            if not isinstance(value_pair, list) or len(value_pair) != 2:
                continue
            try:
                value = float(value_pair[1])
            except Exception:
                continue
            samples.append(PrometheusSample(labels={str(k): str(v) for k, v in metric.items()}, value=value))

        return samples

    async def query_range(
        self,
        promql: str,
        start: float,
        end: float,
        step_seconds: int,
    ) -> List[Tuple[Dict[str, str], List[float]]]:
        params: Dict[str, Any] = {
            "query": promql,
            "start": start,
            "end": end,
            "step": step_seconds,
        }

        payload = await self._get_json("/api/v1/query_range", params=params)

        if payload.get("status") != "success":
            raise PrometheusQueryError(str(payload))

        data = payload.get("data") or {}
        result = data.get("result") or []

        out: List[Tuple[Dict[str, str], List[float]]] = []
        for item in result:
            metric = item.get("metric") or {}
            values = item.get("values") or []
            series: List[float] = []
            for pair in values:
                if not isinstance(pair, list) or len(pair) != 2:
                    continue
                try:
                    series.append(float(pair[1]))
                except Exception:
                    series.append(0.0)
            out.append(({str(k): str(v) for k, v in metric.items()}, series))

        return out


async def prom_scalar(client: PrometheusClient, promql: str, default: float = 0.0) -> float:
    samples = await client.query(promql)
    if not samples:
        return default
    return float(samples[0].value)


async def prom_label_values(
    client: PrometheusClient,
    promql: str,
    label: str,
    default: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    samples = await client.query(promql)
    if not samples:
        return default or {}

    out: Dict[str, float] = {}
    for s in samples:
        key = s.labels.get(label) or "unknown"
        out[key] = out.get(key, 0.0) + float(s.value)
    return out
