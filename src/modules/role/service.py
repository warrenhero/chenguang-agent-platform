from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BizException
from src.modules.permission.repository import PermissionRepository
from src.modules.role.model import Role, user_roles
from src.modules.role.repository import RoleRepository
from src.modules.role.schema import RoleCreate, RoleUpdate
from src.utils.permission_cache import PermissionCache


class RoleService:
    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        self.db = db
        self.repo = RoleRepository(db)
        self.permission_repo = PermissionRepository(db)
        self.perm_cache = PermissionCache(redis) if redis else None

    async def create_role(self, data: RoleCreate) -> Role:
        # 检查 code 是否已存在
        role = await self.repo.get_by_code(data.code)
        if role:
            raise BizException(message=f"角色 {data.code}-{data.name} 已经存在")

        role = Role(**data.model_dump())
        role = await self.repo.create(role)
        return role

    async def get_role(self, role_id: int) -> Role:
        # 查不到抛异常
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise BizException(code=404, message=f"角色 {role_id} 不存在")
        return role

    async def list_roles(self) -> list[Role]:
        roles = await self.repo.get_all()
        return roles

    async def update_role(self, role_id: int, data: RoleUpdate) -> Role:
        # 查不到抛异常
        role = await self.get_role(role_id)
        if not role:
            raise BizException(code=404, message=f"角色 {role_id} 不存在")
        role.name = data.name or role.name
        role.description = data.description or role.description
        role = await self.repo.update(role)
        return role

    async def delete_role(self, role_id: int) -> None:
        role = await self.get_role(role_id)
        if not role:
            raise BizException(code=404, message="角色不存在")
        # 删除前记录受影响用户：级联删除后 user_roles 已查不到
        affected_user_ids = await self._user_ids_for_role(role_id)
        await self.repo.delete(role)
        await self.db.commit()
        if self.perm_cache:
            await self.perm_cache.delete_user_cache_batch(affected_user_ids)
        return None

    async def _user_ids_for_role(self, role_id: int) -> list[int]:
        stmt = select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def assign_permissions(self, role_id: int, permission_ids: list[int]) -> Role:
        # 这是本节的重点方法！
        # 1. 查找角色，不存在抛异常
        role = await self.get_role(role_id)
        if not role:
            raise BizException(code=404, message=f"角色 {role_id} 不存在")
        # 2. 逐个查询 Permission，过滤掉不存在的 ID
        permission_list = [
            p
            for pid in permission_ids
            if (p := await self.permission_repo.get_by_id(pid)) is not None
        ]

        # 3. 校验：如果查到的数量 != 传入的数量，说明有无效 ID，抛异常
        if len(permission_list) != len(permission_ids):
            raise BizException(message="权限 ID 列表中包含无效 ID")

        # 4. 直接替换角色的权限列表：role.permissions = permission_list
        role.permissions = permission_list

        # 5. flush + refresh
        await self.repo.update(role)

        # 先在事务内收集受影响用户，提交后再失效缓存
        affected_user_ids = await self._user_ids_for_role(role_id)
        await self.db.commit()
        if self.perm_cache:
            await self.perm_cache.delete_user_cache_batch(affected_user_ids)

        # 6. 返回更新后的 role（会自动带上新的 permissions）
        return role

    # 分页搜索
    async def search_page(
        self, offset: int, limit: int, keyword: str | None
    ) -> tuple[list[Role], int]:
        return await self.repo.search_page(offset=offset, limit=limit, keyword=keyword)
