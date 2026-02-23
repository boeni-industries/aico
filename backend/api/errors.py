from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel


class APIErrorResponse(BaseModel):
    error_code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None


def raise_api_error(*, status_code: int, error_code: str, message: str, details: Any | None = None) -> None:
    detail: dict[str, Any] = {"error_code": error_code, "message": message}
    if details is not None:
        detail["details"] = details
    raise HTTPException(status_code=status_code, detail=detail)


def error_responses(*status_codes: int) -> dict[int, dict[str, object]]:
    return {
        int(code): {"model": APIErrorResponse}
        for code in status_codes
    }
