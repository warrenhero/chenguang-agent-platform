from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.exceptions import BizException
from src.core.base_schema import PageResult
from src.core.deps import PageParams
from src.modules.prompt.model import Prompt, PromptVersion
from src.modules.prompt.repository import (
    PromptRepository, PromptVersionRepository, parse_version,
)
from src.modules.prompt.schema import (
    PromptCreate, PromptUpdate, PromptRead,
    PromptVersionRead, PublishRequest, RollbackRequest,
)


class PromptService:
    def __init__(self, db: AsyncSession):
        self.repo = PromptRepository(db)
        self.version_repo = PromptVersionRepository(db)

    def _to_read(self, prompt: Prompt) -> PromptRead:
        return PromptRead(
            id=prompt.id,
            name=prompt.name,
            description=prompt.description,
            category=prompt.category,
            tags=prompt.tags or [],
            content=prompt.content,
            variables=prompt.variables or [],
            version=prompt.version,
            status=prompt.status,
            created_by=prompt.created_by,
        )

    async def create_prompt(
        self, data: PromptCreate, current_user: str | None = None
    ) -> PromptRead:
        prompt = Prompt(
            name=data.name,
            description=data.description,
            category=data.category,
            tags=data.tags,
            content=data.content,
            variables=[v.model_dump() for v in data.variables],
            version="v0.1",
            status="draft",
            created_by=current_user,
        )
        prompt = await self.repo.create(prompt)
        return self._to_read(prompt)

    async def get_prompt(self, prompt_id: int) -> PromptRead:
        prompt = await self.repo.get_by_id(prompt_id)
        if not prompt:
            raise BizException(code=42001, message="Prompt 不存在")
        return self._to_read(prompt)

    async def list_prompts(self, params: PageParams) -> PageResult[PromptRead]:
        """分页查询 Prompt 列表"""
        items, total = await self.repo.search_page(
            offset=params.offset,
            limit=params.page_size,
            keyword=params.keyword,
        )
        return PageResult(
            items=[self._to_read(p) for p in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def update_prompt(self, prompt_id: int, data: PromptUpdate) -> PromptRead:
        prompt = await self.repo.get_by_id(prompt_id)
        if not prompt:
            raise BizException(code=42001, message="Prompt 不存在")

        if data.name is not None:
            prompt.name = data.name
        if data.description is not None:
            prompt.description = data.description
        if data.category is not None:
            prompt.category = data.category
        if data.tags is not None:
            prompt.tags = data.tags
        if data.content is not None:
            prompt.content = data.content
        if data.variables is not None:
            prompt.variables = [v.model_dump() for v in data.variables]

        prompt = await self.repo.update(prompt)
        return self._to_read(prompt)

    async def delete_prompt(self, prompt_id: int) -> None:
        prompt = await self.repo.get_by_id(prompt_id)
        if not prompt:
            raise BizException(code=42001, message="Prompt 不存在")
        await self.repo.delete_by_id(prompt_id)

    async def publish(
        self, prompt_id: int, data: PublishRequest, current_user: str | None = None
    ) -> PromptRead:
        """发布新版本"""
        prompt = await self.repo.get_by_id(prompt_id)
        if not prompt:
            raise BizException(code=42001, message="Prompt 不存在")

        # 1. 基于已有版本快照计算新版本号（首次发布为 v1.0）
        new_version = self._next_version(
            await self.version_repo.get_max_version(prompt_id)
        )

        # 2. 将旧版本的 is_current 设为 False
        await self.version_repo.clear_current(prompt_id)

        # 3. 创建版本快照
        version = PromptVersion(
            prompt_id=prompt_id,
            version=new_version,
            content=prompt.content,
            changelog=data.changelog,
            is_current=True,
            published_by=current_user,
            published_at=datetime.now(),
        )
        try:
            await self.version_repo.create(version)
        except IntegrityError as exc:
            # 并发发布撞上 (prompt_id, version) 唯一约束：回滚失败事务后转为业务异常
            await self.repo.db.rollback()
            raise BizException(code=409, message="版本冲突，请重试") from exc

        # 4. 更新 Prompt 主表
        prompt.version = new_version
        prompt.status = "published"
        await self.repo.update(prompt)

        return self._to_read(prompt)

    async def get_versions(self, prompt_id: int) -> list[PromptVersionRead]:
        """获取版本列表"""
        versions = await self.version_repo.get_versions_by_prompt(prompt_id)
        return [PromptVersionRead.model_validate(v) for v in versions]

    async def rollback(self, prompt_id: int, data: RollbackRequest) -> PromptRead:
        """回滚到指定版本"""
        prompt = await self.repo.get_by_id(prompt_id)
        if not prompt:
            raise BizException(code=42001, message="Prompt 不存在")

        # 1. 查找目标版本
        target_version = await self.version_repo.get_by_version(prompt_id, data.version)
        if not target_version:
            raise BizException(code=404, message="版本不存在")

        # 2. 用目标版本的内容覆盖当前内容
        prompt.content = target_version.content
        prompt.version = target_version.version

        # 3. 更新 is_current 标记
        await self.version_repo.clear_current(prompt_id)
        target_version.is_current = True
        await self.version_repo.update(target_version)

        await self.repo.update(prompt)
        return self._to_read(prompt)

    @staticmethod
    def _next_version(current: str | None) -> str:
        """基于已有最大版本号递增 minor：v1.2 → v1.3；无版本或解析失败时为 v1.0"""
        parsed = parse_version(current) if current else None
        if parsed is None:
            return "v1.0"
        major, minor = parsed
        return f"v{major}.{minor + 1}"
