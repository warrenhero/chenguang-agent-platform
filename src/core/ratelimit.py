from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.core.config import get_settings
from src.core.exceptions import BizException

# 原子地自增并在首次写入时设置 TTL。
# 用 Lua 而不是 INCR + EXPIRE NX：EXPIRE NX 需要 Redis 7+，低版本会静默 fail-open。
_INCR_WITH_EXPIRE = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def hit(redis: Redis, key: str, limit: int, window: int) -> None:
    """自增计数并检查：超过 limit 抛 429。用于按请求计数的限流。"""
    if not get_settings().RATE_LIMIT_ENABLED:
        return
    try:
        count = int(await redis.eval(_INCR_WITH_EXPIRE, 1, key, window))
    except RedisError:
        # fail-open：限流组件故障时不阻断业务，仅记录告警
        logger.warning(f"限流检查失败，已放行: key={key}", exc_info=True)
        return
    if count > limit:
        raise BizException(code=429, message="操作过于频繁，请稍后再试")


async def check(redis: Redis, key: str, limit: int) -> None:
    """只读检查：计数达到 limit 即拒绝，不递增。用于校验密码前的账号锁定判断。"""
    if not get_settings().RATE_LIMIT_ENABLED:
        return
    try:
        count = int(await redis.get(key) or 0)
    except RedisError:
        logger.warning(f"限流检查失败，已放行: key={key}", exc_info=True)
        return
    if count >= limit:
        raise BizException(code=429, message="操作过于频繁，请稍后再试")


async def record_failure(redis: Redis, key: str, window: int) -> None:
    """记录一次失败，计数窗口从首次失败开始计算。"""
    if not get_settings().RATE_LIMIT_ENABLED:
        return
    try:
        await redis.eval(_INCR_WITH_EXPIRE, 1, key, window)
    except RedisError:
        logger.warning(f"限流计数失败: key={key}", exc_info=True)


async def reset(redis: Redis, key: str) -> None:
    """清除计数，例如登录成功后解除账号锁定。"""
    if not get_settings().RATE_LIMIT_ENABLED:
        return
    try:
        await redis.delete(key)
    except RedisError:
        logger.warning(f"限流计数清除失败: key={key}", exc_info=True)
