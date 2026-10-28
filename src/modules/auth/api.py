from fastapi import APIRouter, Depends
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
    )-> AuthService:
    """获取认证服务"""
    return AuthService(db, redis)

@router.post("/login", response_model=ResponseSchema[TokenResponse], summary="用户登录")
async def login(
    data: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
):
    token = await svc.login(data)
    return ResponseSchema(data=token)