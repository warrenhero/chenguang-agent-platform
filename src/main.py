from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.core.bootstrap import bootstrap_rbac
from src.core.config import get_settings
from src.core.exceptions import register_exception_handlers
from src.core.logger import setup_logger
from src.infra.database import AsyncSessionLocal, engine
from src.middlewares.logging import LoggingMiddleware
from src.modules.auth.api import router as auth_router
from src.modules.captcha.api import router as captcha_router
from src.modules.model.api import router as model_router
from src.modules.permission.api import router as permission_router
from src.modules.prompt.api import router as prompt_router
from src.modules.provider.api import router as provider_router
from src.modules.role.api import router as role_router
from src.modules.user.api import router as user_router


# 使用上下文管理器感知项目的生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    settings = get_settings()
    logger.info(f"{settings.APP_NAME} starting | env={settings.APP_ENV}")
    # 幂等初始化权限/角色/初始管理员，避免 RBAC 上线后无人可登录管理
    async with AsyncSessionLocal() as db:
        await bootstrap_rbac(
            db,
            superuser_username=settings.BOOTSTRAP_SUPERUSER_USERNAME,
            superuser_password=settings.BOOTSTRAP_SUPERUSER_PASSWORD,
            superuser_email=settings.BOOTSTRAP_SUPERUSER_EMAIL,
        )
    yield
    await engine.dispose()
    logger.info(f"{settings.APP_NAME} shutdown")

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.APP_DEBUG,
        lifespan=lifespan,
    )

    # 异常处理
    register_exception_handlers(app)

    # 中间件
    app.add_middleware(LoggingMiddleware)
    # 前端开发服务器跨域访问：放行本机任意端口（localhost / 127.0.0.1）
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册模块路由
    app.include_router(user_router, prefix="/api/v1")
    app.include_router(captcha_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(permission_router, prefix="/api/v1")  # 注册权限模块路由
    app.include_router(role_router, prefix="/api/v1")  # 注册角色模块路由
    app.include_router(provider_router, prefix="/api/v1") # 注册供应商模块路由
    app.include_router(model_router, prefix="/api/v1") # 注册模型模块路由
    app.include_router(prompt_router, prefix="/api/v1") # 注册提示模块路由

    return app

app = create_app()

# 健康检查端点
@app.get("/health")
async def root():
    return {"status": "ok"}


# def main():
#     import uvicorn

#     uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)


# if __name__ == "__main__":
#     main()
