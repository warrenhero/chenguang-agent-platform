from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_repository import BaseRepository
from src.modules.permission.model import Permission


class PermissionRepository(BaseRepository[Permission]):
    SEARCH_FIELDS = ["name", "code"]    # 定义可搜索的字段列表，用于分页搜索功能

    def __init__(self, db: AsyncSession):
        super().__init__(Permission, db)    # 调用父类的构造函数，传入 Permission 模型和数据库会话对象

    async def get_by_code(self, code: str) -> Permission | None:
        # 根据 code 查询权限, code 是唯一的，所以返回值是 Permission 或 None
        return await self.db.scalar(        # scalar 方法用于执行查询并返回单个结果，如果没有结果则返回 None
            select(Permission).filter(Permission.code == code)
        )


    # 分页搜索
    async def search_page(
        self, offset: int, limit: int, keyword: str | None
    ) -> tuple[list[Permission], int]:
        return await self.get_page(
            offset=offset,
            limit=limit,
            keyword=keyword,
            search_fields=self.SEARCH_FIELDS,
        )