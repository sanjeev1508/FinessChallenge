"""One consistent error envelope for every failure:

{"error": {"code": "VALIDATION_ERROR", "message": "...", "details": [{"field": "...", "message": "..."}]}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("fitness")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, extra: dict | None = None):
        self.status, self.code, self.message, self.extra = status, code, message, extra or {}


def _body(code: str, message: str, details: list | None = None, **extra) -> dict:
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    err.update(extra)
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message, **exc.extra))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # FastAPI defaults to 422; the spec requires 400 Bad Request.
        details, code = [], "VALIDATION_ERROR"
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", ()) if p not in ("body",)]
            if e.get("type") == "sport_metric_mismatch":
                code = "SPORT_METRIC_MISMATCH"
            if e.get("type") == "json_invalid":
                code = "INVALID_JSON"
            msg = str(e.get("msg", "invalid value")).removeprefix("Value error, ")
            details.append({"field": ".".join(loc) or "body", "message": msg})
        summary = {"SPORT_METRIC_MISMATCH": "Sport and metric type do not match.",
                   "INVALID_JSON": "Request body is not valid JSON."}.get(code, "Request body failed validation.")
        return JSONResponse(status_code=400, content=_body(code, summary, details))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "Something went wrong on the server."))
