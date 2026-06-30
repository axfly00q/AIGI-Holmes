"""
AIGI-Holmes backend — custom exception classes and FastAPI handlers.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    def __init__(self, code: int, message: str, detail: str | None = None):
        self.code = code
        self.message = message
        self.detail = detail


class ImageFormatError(AppError):
    def __init__(self, detail: str | None = None):
        super().__init__(400, "无法解析图片文件，请上传有效的图片。", detail)


class ModelInferenceError(AppError):
    def __init__(self, detail: str | None = None):
        super().__init__(500, "模型推理失败，请稍后重试。", detail)


class AuthError(AppError):
    def __init__(self, message: str = "认证失败", detail: str | None = None):
        super().__init__(401, message, detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str | None = None):
        super().__init__(403, "权限不足", detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )
