"""
Standardized API response models.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: ErrorDetail


class SuccessResponse(BaseModel, Generic[T]):
    """Standardized success response wrapper."""
    data: T
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


def create_error_response(code: str, message: str, details: Dict[str, Any] = None) -> ErrorResponse:
    """Create a standardized error response."""
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details
        )
    )

