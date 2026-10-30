from redis.asyncio import Redis
from sqlalchemy import select

from src.core.exceptions import BizException
from src.infra.database import AsyncSession
from src.modules.permission.model import Permission
from src.modules.permission.repository import PermissionRepository
from src.modules.permission.schema import PermissionCreate, PermissionUpdate
from src.modules.role.model import role_permissions, user_roles
from src.utils.permission_cache import PermissionCache


class PermissionService:
    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        self.db = db
        self.repo = PermissionRepository(db)
        self.perm_cache = PermissionCache(redis) if redis else None

    async def create_permission(self, data: PermissionCreate) -> Permission:
        # 1. 检查 code 是否已存在，已存在则抛 BizException
        existing = await self.repo.get_by_code(data.code)
        if existing:
            raise BizException(code=400, message="权限码已经存在")

        # 2. 创建 Permission 对象
        permission = Permission(
            code=data.code,
            name=data.name,
            description=data.description
        )
        await self.repo.create(permission)
        return permission

    async def get_permission(self, permission_id: int) -> Permission:
        # 查不到抛 BizException(code=404)
        permission = await self.repo.get_by_id(permission_id)
        if not permission:
            raise BizException(code=404, message="权限不存在")
        return permission

    async def list_permissions(self) -> list[Permission]:
        # 调用 repo.get_all()
        return await self.repo.get_all()

    async def update_permission(self, permission_id: int, data: PermissionUpdate) -> Permission:
        # 1. 查找权限，不存在抛异常
        permission = await self.get_permission(permission_id)
        if not permission:
            raise BizException(code=404, message="权限不存在")
        # 2. 只更新 data 中非 None 的字段
        if data.name is not None:
            permission.name = data.name
        if data.description is not None:
            permission.description = data.description
        # 3. 调用 repo.update()
        await self.repo.update(permission)
        return permission

    async def delete_permission(self, permission_id: int) -> None:
        # 1. 查找权限，不存在抛异常
        permission = await self.get_permission(permission_id)
        if not permission:
            raise BizException(code=404, message="权限不存在")
        # 2. 删除前记录受影响用户：级联删除后关联表已查不到
        affected_user_ids = await self._user_ids_for_permission(permission_id)
        # 3. 调用 repo.delete()
        await self.repo.delete(permission)
        await self.db.commit()
        if self.perm_cache:
            await self.perm_cache.delete_user_cache_batch(affected_user_ids)
        return None

    async def _user_ids_for_permission(self, permission_id: int) -> list[int]:
        stmt = (
            select(user_roles.c.user_id)
            .distinct()
            .join(
                role_permissions,
                role_permissions.c.role_id == user_roles.c.role_id,
            )
            .where(role_permissions.c.permission_id == permission_id)
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    # 分页搜索
    async def search_page(
        self, offset: int, limit: int, keyword: str | None
    ) -> tuple[list[Permission], int]:
        return await self.repo.search_page(offset=offset, limit=limit, keyword=keyword)
