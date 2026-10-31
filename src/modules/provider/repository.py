from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_repository import BaseRepository
from src.modules.provider.model import ModelProvider


class ProviderRepository(BaseRepository[ModelProvider]):
    """搜索字段：按名称或类型搜索"""
    SEARCH_FIELDS = ["name", "type"]

    def __init__(self, db: AsyncSession):
        super().__init__(ModelProvider, db)

    async def get_by_name(self, name: str) -> ModelProvider | None:
        """按名称查找供应商（用于创建时去重）"""
        stmt = select(ModelProvider).where(ModelProvider.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_models(self, provider_id: int) -> int:
        """统计供应商下的模型数量。

        模型模块尚未实现（当前无 models 表），先返回 0；模型表落地后改为
        select(func.count()).select_from(Model).where(Model.provider_id == provider_id)
        """
        return 0

    async def search_page(
        self, offset: int, limit: int, keyword: str | None
    ) -> tuple[list[ModelProvider], int]:
        """分页 + 搜索（调用 BaseRepository.get_page）"""
        return await self.get_page(
            offset=offset,
            limit=limit,
            keyword=keyword,
            search_fields=self.SEARCH_FIELDS,
        )