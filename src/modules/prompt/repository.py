from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.base_repository import BaseRepository
from src.modules.prompt.model import Prompt, PromptVersion


def parse_version(version: str) -> tuple[int, int] | None:
    """把 v<major>.<minor> 解析为数值元组，无法解析时返回 None。"""
    try:
        major, minor = version.removeprefix("v").split(".")
        return int(major), int(minor)
    except ValueError:
        return None


class PromptRepository(BaseRepository[Prompt]):
    """搜索字段：按名称或分类搜索"""
    SEARCH_FIELDS = ["name", "category"]

    def __init__(self, db: AsyncSession):
        super().__init__(Prompt, db)

    async def get_by_name(self, name: str) -> Prompt | None:
        stmt = select(Prompt).where(Prompt.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_page(
        self, offset: int, limit: int, keyword: str | None
    ) -> tuple[list[Prompt], int]:
        """分页 + 搜索"""
        return await self.get_page(
            offset=offset,
            limit=limit,
            keyword=keyword,
            search_fields=self.SEARCH_FIELDS,
        )


class PromptVersionRepository(BaseRepository[PromptVersion]):
    def __init__(self, db: AsyncSession):
        super().__init__(PromptVersion, db)

    async def get_versions_by_prompt(self, prompt_id: int) -> list[PromptVersion]:
        """获取某个 Prompt 的所有版本，按 ID 倒序"""
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.id.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_version(self, prompt_id: int, version: str) -> PromptVersion | None:
        """按版本号查找某个 Prompt 的版本快照"""
        stmt = select(PromptVersion).where(
            PromptVersion.prompt_id == prompt_id,
            PromptVersion.version == version,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_max_version(self, prompt_id: int) -> str | None:
        """返回该 Prompt 下数值最大的版本号；无版本或均无法解析时返回 None"""
        stmt = select(PromptVersion.version).where(
            PromptVersion.prompt_id == prompt_id
        )
        result = await self.db.execute(stmt)
        best: tuple[int, int] | None = None
        best_raw: str | None = None
        for raw in result.scalars().all():
            parsed = parse_version(raw)
            if parsed is None:
                continue
            if best is None or parsed > best:
                best, best_raw = parsed, raw
        return best_raw

    async def clear_current(self, prompt_id: int) -> None:
        """将某个 Prompt 的所有版本的 is_current 设为 False"""
        stmt = (
            update(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .values(is_current=False)
        )
        await self.db.execute(stmt)