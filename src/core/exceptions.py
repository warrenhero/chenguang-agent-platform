from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


class BizException(Exception):
    """业务异常"""
    def __init__(self, code: int = 400, message: str = "业务异常"):
        self.code = code
        self.message = message


# 业务码与 HTTP 状态保持一致，网关/前端可依据状态码做统一处理
_HTTP_STATUS = {401: 401, 403: 403, 404: 404, 409: 409, 429: 429}

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        return JSONResponse(
            status_code=_HTTP_STATUS.get(exc.code, 400),
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )