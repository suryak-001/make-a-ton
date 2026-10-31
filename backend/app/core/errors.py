"""Owner: A. Services raise these; the handler registered in main.py turns them into JSON responses.

Error bodies follow FastAPI's validation format when tied to a form field
(`detail: [{loc: ["body", field], msg}]`) and are `detail: "message"` otherwise, so the frontend's
ApiError can show either one.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class Invalid(DomainError):
    status_code = 422


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        detail = [{"loc": ["body", exc.field], "msg": exc.message}] if exc.field else exc.message
        return JSONResponse({"detail": detail}, status_code=exc.status_code)
