"""OptiVest FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import APIError


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": None, "error": {"code": code, "message": message}},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="OptiVest API", version="1.0.0", debug=settings.debug)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(APIError)
    async def handle_api_error(_request: Request, error: APIError) -> JSONResponse:
        return error_response(error.status_code, error.code, error.message)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        message = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        return error_response(422, "VALIDATION_ERROR", message)

    @application.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, error: HTTPException) -> JSONResponse:
        return error_response(error.status_code, "HTTP_ERROR", str(error.detail))

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        message = str(error) if settings.debug else "An unexpected server error occurred"
        return error_response(500, "INTERNAL_ERROR", message)

    application.include_router(api_router)
    return application


app = create_app()
