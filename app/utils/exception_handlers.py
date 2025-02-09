from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Simplify validation error response"""
    errors = []
    for error in exc.errors():
        # Extract field name and error message
        field = error["loc"][-1] if error["loc"] else "unknown field"
        message = error["msg"]

        # Create simplified error message
        error_msg = f"{field}: {message}"
        errors.append(error_msg)

    logger.error(f"Validation error: {errors}")

    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "type": "validation_error",
            "errors": errors
        }
    )