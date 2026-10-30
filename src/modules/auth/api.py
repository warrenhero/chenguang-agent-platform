from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_schema import ResponseSchema
from src.infra.database import get_db
from src.infra.redis_cache import get_redis
from src.modules.auth.schema import LoginRequest, TokenResponse
from src.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


# 依赖注入 AuthService
def get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthService:
    """获取认证服务"""
    return AuthService(db, redis)


@router.post("/login", response_model=ResponseSchema[TokenResponse], summary="用户登录")
async def login(
    data: LoginRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    client_ip = request.client.host if request.client else "unknown"
    token = await svc.login(data, client_ip=client_ip)
    return ResponseSchema(data=token)
