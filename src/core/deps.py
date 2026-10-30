from fastapi import Depends, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import BizException
from src.infra.database import get_db
from src.infra.redis_cache import get_redis
from src.modules.role.model import Role
from src.modules.user.model import User
from src.utils.jwt_utils import oauth2_scheme, verify_jwt
from src.utils.permission_cache import PermissionCache


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT token 中解析当前登录用户，用于保护接口。

    只读取用户本身；角色/权限在 require_permission 中按需从缓存或数据库获取。
    """
    try:
        payload = verify_jwt(token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise BizException(code=401, message="未登录或 token 已过期")

    stmt = (
        select(User)
        .where(User.id == user_id)
        .execution_options(populate_existing=True)
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise BizException(code=401, message="用户不存在")
    if not user.is_active:
        raise BizException(code=401, message="账号已被禁用")

    return user


def require_permission(permission_code: str):
    """
    返回一个 FastAPI 依赖函数，用于校验当前用户是否拥有指定权限。

    使用方式:Depends(require_permission("user:read"))
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
    ) -> User:
        # 1. 超级管理员直接放行
        if current_user.is_superuser:
            return current_user

        # 2. 优先读缓存；未命中或缓存不可用时回源数据库
        perm_cache = PermissionCache(redis)
        user_permissions = await perm_cache.get_permissions(current_user.id)
        if user_permissions is None:
            stmt = (
                select(User)
                .where(User.id == current_user.id)
                .options(selectinload(User.roles).selectinload(Role.permissions))
                .execution_options(populate_existing=True)
            )
            user = (await db.execute(stmt)).scalar_one_or_none()
            user_permissions = {
                perm.code
                for role in (user.roles if user else ())
                for perm in role.permissions
            }
            await perm_cache.set_permissions(current_user.id, user_permissions)

        # 3. 检查目标权限是否在集合中
        if permission_code not in user_permissions:
            raise BizException(code=403, message=f"无权限: {permission_code}")

        return current_user

    return _check


class PageParams:
    """通用分页参数，通过 Depends 注入到接口中"""
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码,从1开始"),
        page_size: int = Query(10, ge=1, le=100, description="每页条数"),
        keyword: str | None = Query(None, description="搜索关键词"),
    ):
        self.page = page
        self.page_size = page_size
        self.keyword = keyword

    @property
    def offset(self) -> int:
        """计算 SQL OFFSET"""
        return (self.page - 1) * self.page_size 