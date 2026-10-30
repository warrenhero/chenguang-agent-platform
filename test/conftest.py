import os
import uuid

# 必须在导入 src 之前设置：jwt_utils 在导入时读取并校验 JWT_SECRET
# 环境变量优先级高于 .env，测试固定用假密钥，不依赖本地真实配置
os.environ.setdefault("JWT_SECRET_KEY", "x" * 64)
# 测试中关闭限流，避免用例之间互相计数
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.infra.database import get_db
from src.infra.redis_cache import get_redis
from src.main import app
from src.modules.user.model import User
from src.utils.jwt_utils import encode_jwt


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
async def superuser_headers(db_session):
    """在测试事务内创建一个超级管理员，后续请求默认携带其 token。

    受保护接口需要权限，普通用例不必关心 RBAC 细节；
    需要验证匿名/无权限路径的用例改用 anon_client 或传入其他用户的 token。
    """
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"admin_{suffix}",
        email=f"admin_{suffix}@example.com",
        hashed_password="not-used",
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    token = encode_jwt({"sub": str(user.id), "username": user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(db_session, redis_client, superuser_headers):
    """把应用的 get_db/get_redis 依赖替换成测试实例，接口与业务共用同一事务。

    默认以超级管理员身份请求；需要匿名访问时使用 anon_client。
    """

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=superuser_headers
    ) as c:
        try:
            yield c
        finally:
            app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client(client):
    """复用 client 的依赖覆盖，但不带任何认证头。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


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
