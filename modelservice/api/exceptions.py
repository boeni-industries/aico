"""
Custom exceptions for modelservice API.
"""

from fastapi import HTTPException


class ModelServiceException(HTTPException):
    """Base exception for modelservice errors."""
    pass


class ModelNotFoundError(ModelServiceException):
    """Raised when a requested model is not found."""
    def __init__(self, model_name: str):
        super().__init__(status_code=404, detail=f"Model '{model_name}' not found")


class ModelLoadError(ModelServiceException):
    """Raised when a model fails to load."""
    def __init__(self, model_name: str, reason: str = "Unknown error"):
        super().__init__(status_code=500, detail=f"Failed to load model '{model_name}': {reason}")


# TODO: Add additional exceptions as needed