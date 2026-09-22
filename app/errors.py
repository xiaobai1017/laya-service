from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_response(status: int, message: str, param: str | None = None) -> JSONResponse:
    body: dict[str, Any] = {"error": {"type": "invalid_request_error", "message": message}}
    if param:
        body["error"]["param"] = param
    return JSONResponse(status_code=status, content=body)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []))
    return error_response(422, first.get("msg", "Invalid request"), loc or None)

