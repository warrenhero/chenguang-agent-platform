import uuid

import pytest
from redis.exceptions import RedisError

from src.core.exceptions import BizException
from src.core import ratelimit

pytestmark = pytest.mark.asyncio


class _EnabledSettings:
    RATE_LIMIT_ENABLED = True


class _BrokenRedis:
    async def eval(self, *args, **kwargs):
        raise RedisError("boom")

    async def get(self, *args, **kwargs):
        raise RedisError("boom")

    async def delete(self, *args, **kwargs):
        raise RedisError("boom")


@pytest.fixture(autouse=True)
def enable_ratelimit(monkeypatch):
    monkeypatch.setattr(ratelimit, "get_settings", lambda: _EnabledSettings())


def _key() -> str:
    return f"test:rl:{uuid.uuid4().hex}"


async def test_hit_allows_up_to_limit(redis_client):
    key = _key()
    try:
        for _ in range(3):
            await ratelimit.hit(redis_client, key, 3, 60)
        assert int(await redis_client.get(key)) == 3
        assert await redis_client.ttl(key) > 0
    finally:
        await redis_client.delete(key)


async def test_hit_blocks_over_limit(redis_client):
    key = _key()
    try:
        for _ in range(3):
            await ratelimit.hit(redis_client, key, 3, 60)
        with pytest.raises(BizException) as exc_info:
            await ratelimit.hit(redis_client, key, 3, 60)
        assert exc_info.value.code == 429
    finally:
        await redis_client.delete(key)


async def test_check_does_not_increment(redis_client):
    key = _key()
    try:
        await ratelimit.check(redis_client, key, 1)
        assert await redis_client.get(key) is None
    finally:
        await redis_client.delete(key)


async def test_check_blocks_after_failures(redis_client):
    key = _key()
    try:
        await ratelimit.record_failure(redis_client, key, 900)
        await ratelimit.check(redis_client, key, 2)
        await ratelimit.record_failure(redis_client, key, 900)
        with pytest.raises(BizException) as exc_info:
            await ratelimit.check(redis_client, key, 2)
        assert exc_info.value.code == 429
    finally:
        await redis_client.delete(key)


async def test_reset_clears_failures(redis_client):
    key = _key()
    try:
        await ratelimit.record_failure(redis_client, key, 900)
        await ratelimit.reset(redis_client, key)
        assert await redis_client.get(key) is None
        await ratelimit.check(redis_client, key, 1)
    finally:
        await redis_client.delete(key)


async def test_fail_open_on_redis_error():
    # Redis 故障时不阻断业务
    await ratelimit.hit(_BrokenRedis(), "k", 1, 60)
    await ratelimit.check(_BrokenRedis(), "k", 1)
    await ratelimit.record_failure(_BrokenRedis(), "k", 60)
    await ratelimit.reset(_BrokenRedis(), "k")
