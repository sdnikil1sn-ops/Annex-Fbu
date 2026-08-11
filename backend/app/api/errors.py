"""Error model and exception handlers.

All failures are normalized into the documented machine-readable envelope:

    {"error": {"code", "message", "request_id", "details"?}}

See docs/api/v1-endpoints.md for the envelope contract. Internal details
are never leaked to clients — unhandled exceptions produce a generic
``internal.error`` envelope while the full trace is logged server-side.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger("app")


class AppError(Exception):
    """Application-level error with a stable machine-readable code.

    Args:
        code: Stable error code, e.g. ``analysis.not_found``.
        message: Human-readable summary for the client.
        status_code: HTTP status code for the response.
        details: Optional structured details (validated client data).
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an error envelope carrying the current request ID."""
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_var.get(),
        }
    }
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach envelope-producing exception handlers to the application."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Never echo submitted values back: pydantic v2 includes the offending
        # ``input`` in each error entry, which may contain credentials.
        sanitized = [
            {key: value for key, value in entry.items() if key != "input"} for entry in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "validation.invalid_input",
                "Request validation failed.",
                details={"errors": sanitized},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(f"http.{exc.status_code}", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception while processing %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "internal.error",
                "An unexpected error occurred.",
            ),
        )
