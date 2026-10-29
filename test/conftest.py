import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.infra.database import get_db
from src.infra.redis_cache import get_redis
from src.main import app


@pytest_asyncio.fixture
async def db_session():
    """每个用例包在一个外层事务里，用例结束回滚，不污染数据库"""
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session, redis_client):
    """把应用的 get_db/get_redis 依赖替换成测试实例，接口与业务共用同一事务"""

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        try:
            yield c
        finally:
            app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_permission(client):
    async def _make(
        code: str | None = None,
        name: str = "测试权限",
        description: str | None = None,
    ) -> dict:
        resp = await client.post(
            "/api/v1/permissions",
            json={
                "code": code or f"perm:{uuid.uuid4().hex[:8]}",
                "name": name,
                "description": description,
            },
        )
        body = resp.json()
        assert body["code"] == 200, body
        return body["data"]

    return _make


@pytest_asyncio.fixture
async def make_role(client):
    async def _make(
        code: str | None = None,
        name: str = "测试角色",
        description: str | None = None,
    ) -> dict:
        resp = await client.post(
            "/api/v1/roles",
            json={
                "code": code or f"role:{uuid.uuid4().hex[:8]}",
                "name": name,
                "description": description,
            },
        )
        body = resp.json()
        assert body["code"] == 200, body
        return body["data"]

    return _make


@pytest_asyncio.fixture
async def make_user(client):
    async def _make(
        username: str | None = None,
        email: str | None = None,
        password: str = "Abc@123456",
    ) -> dict:
        suffix = uuid.uuid4().hex[:8]
        resp = await client.post(
            "/api/v1/users",
            json={
                "username": username or f"user_{suffix}",
                "email": email or f"user_{suffix}@example.com",
                "password": password,
            },
        )
        body = resp.json()
        assert body["code"] == 200, body
        return body["data"]

    return _make


@pytest_asyncio.fixture
async def redis_client():
    """每个用例独立的 Redis 客户端，避免连接池跨事件循环复用"""
    settings = get_settings()
    client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def make_captcha(redis_client):
    """在 Redis 中写入一个已知验证码，用例结束清理"""
    created: list[dict] = []

    async def _make(code: str = "AB12") -> dict:
        key = f"test:{uuid.uuid4().hex}"
        await redis_client.set(f"captcha:{key}", code, ex=300)
        captcha = {"key": key, "code": code}
        created.append(captcha)
        return captcha

    yield _make

    for captcha in created:
        await redis_client.delete(f"captcha:{captcha['key']}")
