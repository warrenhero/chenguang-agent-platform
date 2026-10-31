import time

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_schema import PageResult
from src.core.deps import PageParams
from src.core.exceptions import BizException
from src.modules.provider.model import ModelProvider
from src.modules.provider.repository import ProviderRepository
from src.modules.provider.schema import ProviderCreate, ProviderRead, ProviderUpdate
from src.utils.crypto_utils import decrypt_secret, encrypt_secret


class ProviderService:
    def __init__(self, db: AsyncSession):
        self.repo = ProviderRepository(db)

    @staticmethod
    def _to_read(provider: ModelProvider, model_count: int = 0) -> ProviderRead:
        """ORM 转响应模型：api_key 在这里解密后返回前端。"""
        return ProviderRead(
            id=provider.id,
            name=provider.name,
            type=provider.type,
            status=provider.status,
            endpoint=provider.endpoint,
            api_key=decrypt_secret(provider.api_key),
            description=provider.description,
            model_count=model_count,
        )

    async def create_provider(self, data: ProviderCreate) -> ProviderRead:
        # 1. 检查名称是否已存在
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise BizException(code=400, message=f"供应商 '{data.name}' 已存在")

        # 2. 创建 ORM 对象，密钥加密后落库
        provider = ModelProvider(
            name=data.name,
            type=data.type,
            endpoint=data.endpoint,
            api_key=encrypt_secret(data.api_key),
            description=data.description,
            status="disconnected",  # 新建默认未连接
        )

        # 3. 保存到数据库；唯一约束兜底并发写入
        try:
            provider = await self.repo.create(provider)
        except IntegrityError:
            raise BizException(code=400, message=f"供应商 '{data.name}' 已存在")
        return self._to_read(provider, await self.repo.count_models(provider.id))

    async def _get_or_404(self, provider_id: int) -> ModelProvider:
        provider = await self.repo.get_by_id(provider_id)
        if not provider:
            raise BizException(code=404, message="供应商不存在")
        return provider

    async def get_provider(self, provider_id: int) -> ProviderRead:
        provider = await self._get_or_404(provider_id)
        return self._to_read(provider, await self.repo.count_models(provider.id))

    async def list_providers(self, params: PageParams) -> PageResult[ProviderRead]:
        """分页查询供应商列表"""
        items, total = await self.repo.search_page(
            offset=params.offset,
            limit=params.page_size,
            keyword=params.keyword,
        )
        read_items = []
        for item in items:
            read_items.append(
                self._to_read(item, await self.repo.count_models(item.id))
            )
        return PageResult(
            items=read_items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def update_provider(
        self, provider_id: int, data: ProviderUpdate
    ) -> ProviderRead:
        provider = await self._get_or_404(provider_id)

        # 只更新非 None 的字段
        if data.name is not None and data.name != provider.name:
            existing = await self.repo.get_by_name(data.name)
            if existing:
                raise BizException(code=400, message=f"供应商 '{data.name}' 已存在")
            provider.name = data.name
        if data.type is not None:
            provider.type = data.type
        if data.endpoint is not None:
            provider.endpoint = data.endpoint
        if data.api_key is not None:
            provider.api_key = encrypt_secret(data.api_key)
        if data.description is not None:
            provider.description = data.description

        try:
            provider = await self.repo.update(provider)
        except IntegrityError:
            raise BizException(code=400, message=f"供应商 '{provider.name}' 已存在")
        return self._to_read(provider, await self.repo.count_models(provider.id))

    async def delete_provider(self, provider_id: int) -> None:
        # 先确认存在
        await self._get_or_404(provider_id)
        await self.repo.delete_by_id(provider_id)

    async def test_connection(self, provider_id: int) -> dict:
        """测试供应商连接：真实请求 endpoint，拿到响应即视为可达。"""
        provider = await self._get_or_404(provider_id)

        headers = {}
        api_key = decrypt_secret(provider.api_key)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                await client.get(provider.endpoint, headers=headers)
        except httpx.HTTPError as e:
            provider.status = "error"
            await self.repo.update(provider)
            return {"success": False, "message": f"连接失败: {e}"}

        latency_ms = int((time.perf_counter() - started) * 1000)
        provider.status = "connected"
        await self.repo.update(provider)
        return {"success": True, "message": "连接成功", "latency_ms": latency_ms}
