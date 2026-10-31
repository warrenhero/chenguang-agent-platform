from sqlalchemy import func, select
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
        """统计供应商下的模型数量。"""
        # 局部导入：model.model 在模块底部导入 provider.model，模块级导入会成环
        from src.modules.model.model import LLMModel

        stmt = (
            select(func.count())
            .select_from(LLMModel)
            .where(LLMModel.provider_id == provider_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

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