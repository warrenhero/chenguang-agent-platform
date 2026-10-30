import json

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.core.config import get_settings

CACHE_TTL = 1800  # 30 分钟


def permission_cache_key(user_id: int) -> str:
    """缓存 key 带环境前缀，避免多环境共用 Redis 时串权限。"""
    return f"rbac:{get_settings().APP_ENV}:user:perms:{user_id}"


class PermissionCache:
    """用户权限码缓存。

    缓存只存权限码集合；角色不单独缓存，避免两份数据不一致。
    Redis 是派生数据，读写失败一律降级到数据库，不影响业务。
    失效失败不能静默：数据库已变更，缓存可能在 TTL 内保持陈旧。
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_permissions(self, user_id: int) -> set[str] | None:
        """返回 None 表示未命中或缓存不可用，调用方应回源数据库。"""
        try:
            data = await self.redis.get(permission_cache_key(user_id))
        except RedisError:
            logger.warning(f"权限缓存读取失败，回源数据库: user={user_id}", exc_info=True)
            return None
        if data is None:
            return None
        try:
            loaded = json.loads(data)
        except (TypeError, ValueError):
            logger.warning(f"权限缓存内容损坏，按未命中处理: user={user_id}")
            return None
        if not isinstance(loaded, list):
            logger.warning(f"权限缓存结构非法，按未命中处理: user={user_id}")
            return None
        return {str(item) for item in loaded}

    async def set_permissions(self, user_id: int, permissions: set[str]) -> None:
        try:
            await self.redis.set(
                permission_cache_key(user_id),
                json.dumps(sorted(permissions)),
                ex=CACHE_TTL,
            )
        except RedisError:
            logger.warning(f"权限缓存写入失败: user={user_id}", exc_info=True)

    async def delete_user_cache(self, user_id: int) -> None:
        await self.delete_user_cache_batch([user_id])

    async def delete_user_cache_batch(self, user_ids: list[int]) -> None:
        if not user_ids:
            return
        keys = [permission_cache_key(uid) for uid in user_ids]
        try:
            await self.redis.delete(*keys)
        except RedisError:
            logger.error(
                f"权限缓存失效失败，相关用户可能短暂沿用旧权限: users={user_ids}",
                exc_info=True,
            )
