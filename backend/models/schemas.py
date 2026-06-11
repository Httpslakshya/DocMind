from pydantic import BaseModel, Field
from typing import Any, Optional
from fastapi.responses import JSONResponse

class ChatRequest(BaseModel):
    filename: str
    message: str

class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None

class APIErrorResponse(BaseModel):
    success: bool = False
    message: str = "An error occurred"
    error: Optional[Any] = None

def success_response(data: Any = None, message: str = "Operation completed successfully", status_code: int = 200) -> JSONResponse:
    """Helper to generate standardized successful API response."""
    if data is None:
        data = {}
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data
        }
    )

def error_response(message: str, error: Any = None, status_code: int = 400) -> JSONResponse:
    """Helper to generate standardized error API response."""
    if error is None:
        error = {}
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "error": error
        }
    )
