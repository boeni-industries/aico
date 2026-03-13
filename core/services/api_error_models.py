from typing import Any, Optional

from pydantic import BaseModel


class APIErrorResponse(BaseModel):
    error_code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None
