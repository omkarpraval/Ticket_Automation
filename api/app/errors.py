"""Central error envelope: {"error": {"code", "message", "details"}} for every 4xx/5xx response.

Routers should raise ApiError (or let Pydantic/SQLAlchemy raise) rather than
FastAPI's bare HTTPException, so every error on the wire has the same shape.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _envelope(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def not_found(message: str = "Resource not found") -> ApiError:
    return ApiError("NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


def conflict(message: str, details: dict | None = None) -> ApiError:
    return ApiError("CONFLICT", message, status.HTTP_409_CONFLICT, details)


def unauthorized(message: str = "Invalid credentials") -> ApiError:
    return ApiError("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


def validation_error(message: str, details: dict | None = None) -> ApiError:
    return ApiError("VALIDATION_ERROR", message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


def ai_unavailable(message: str = "AI features are unavailable: no GEMINI_API_KEY is configured.") -> ApiError:
    return ApiError("AI_UNAVAILABLE", message, status.HTTP_503_SERVICE_UNAVAILABLE)


def ai_invalid_output(message: str, details: dict | None = None) -> ApiError:
    return ApiError("AI_INVALID_OUTPUT", message, status.HTTP_502_BAD_GATEWAY, details)


def rate_limited(message: str = "The AI provider is rate-limiting requests. Try again shortly.") -> ApiError:
    return ApiError("RATE_LIMITED", message, status.HTTP_429_TOO_MANY_REQUESTS)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("VALIDATION_ERROR", "Request failed validation.", {"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "UNAUTHORIZED", 404: "NOT_FOUND", 409: "CONFLICT", 429: "RATE_LIMITED"}.get(
            exc.status_code, "INTERNAL"
        )
        return JSONResponse(status_code=exc.status_code, content=_envelope(code, str(exc.detail)))

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_envelope("CONFLICT", "The request conflicts with existing data."),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL", "An unexpected error occurred."),
        )
