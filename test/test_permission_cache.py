import uuid

import pytest
from redis.exceptions import RedisError
from sqlalchemy import select

from src.infra.redis_cache import get_redis
from src.main import app
from src.modules.permission.model import Permission
from src.modules.role.model import Role
from src.modules.user.model import User
from src.utils.jwt_utils import encode_jwt
from src.utils.permission_cache import permission_cache_key

pytestmark = pytest.mark.asyncio


class _BrokenRedis:
    async def get(self, *args, **kwargs):
        raise RedisError("boom")

    async def set(self, *args, **kwargs):
        raise RedisError("boom")

    async def delete(self, *args, **kwargs):
        raise RedisError("boom")


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {encode_jwt({'sub': str(user.id)})}"}


async def _get_or_create_permission(db_session, code: str) -> Permission:
    perm = (
        await db_session.execute(select(Permission).where(Permission.code == code))
    ).scalar_one_or_none()
    if perm is None:
        perm = Permission(code=code, name=f"权限 {code}")
        db_session.add(perm)
        await db_session.flush()
    return perm


async def _make_user_with_perms(db_session, codes: list[str]) -> User:
    """创建持有指定权限的普通用户，关系在 flush 前赋值。"""
    suffix = uuid.uuid4().hex[:8]
    permissions = [await _get_or_create_permission(db_session, code) for code in codes]
    role = Role(code=f"cache_role_{suffix}", name="缓存测试角色")
    role.permissions = permissions
    user = User(
        username=f"cache_{suffix}",
        email=f"cache_{suffix}@example.com",
        hashed_password="not-used",
        roles=[role],
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_first_access_caches_permissions(client, db_session, redis_client):
    user = await _make_user_with_perms(db_session, ["user:read"])
    key = permission_cache_key(user.id)
    await redis_client.delete(key)

    resp = await client.get("/api/v1/users", headers=_auth(user))

    assert resp.status_code == 200
    cached = await redis_client.get(key)
    assert cached is not None
    assert '"user:read"' in cached
    await redis_client.delete(key)


async def test_cache_hit_is_authoritative(client, db_session, redis_client):
    user = await _make_user_with_perms(db_session, ["user:read"])
    key = permission_cache_key(user.id)
    await redis_client.delete(key)
    try:
        # 第一次请求回源并写入缓存
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 200

        # 直接修改数据库撤权，缓存仍应继续放行
        user.roles[0].permissions = []
        await db_session.flush()
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 200

        # 清除缓存后，权限校验回源数据库并拒绝
        await redis_client.delete(key)
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 403
    finally:
        await redis_client.delete(key)


async def test_assign_role_permissions_invalidates_cache(
    client, db_session, redis_client
):
    user = await _make_user_with_perms(db_session, ["user:read"])
    role_id = user.roles[0].id
    key = permission_cache_key(user.id)
    await redis_client.delete(key)
    try:
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 200
        assert await redis_client.get(key) is not None

        resp = await client.put(
            f"/api/v1/roles/{role_id}/permissions",
            json={"permission_ids": []},
        )
        assert resp.status_code == 200
        assert await redis_client.get(key) is None

        # 缓存失效后应立刻反映撤权
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 403
    finally:
        await redis_client.delete(key)


async def test_user_role_assignment_invalidates_cache(
    client, db_session, redis_client
):
    user = await _make_user_with_perms(db_session, ["user:read"])
    key = permission_cache_key(user.id)
    await redis_client.delete(key)
    try:
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 200
        assert await redis_client.get(key) is not None

        suffix = uuid.uuid4().hex[:8]
        other_role = Role(code=f"empty_{suffix}", name="空角色")
        db_session.add(other_role)
        await db_session.flush()

        resp = await client.put(
            f"/api/v1/users/{user.id}/roles",
            json={"role_ids": [other_role.id]},
        )
        assert resp.status_code == 200
        assert await redis_client.get(key) is None
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 403
    finally:
        await redis_client.delete(key)


async def test_delete_role_invalidates_cache(client, db_session, redis_client):
    user = await _make_user_with_perms(db_session, ["user:read"])
    role_id = user.roles[0].id
    key = permission_cache_key(user.id)
    await redis_client.delete(key)
    try:
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 200
        assert await redis_client.get(key) is not None

        resp = await client.delete(f"/api/v1/roles/{role_id}")
        assert resp.status_code == 200
        assert await redis_client.get(key) is None
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 403
    finally:
        await redis_client.delete(key)


async def test_delete_permission_invalidates_cache(client, db_session, redis_client):
    # 用接口实际校验的 user:read 验证「删除权限 -> 撤权立即生效」
    user = await _make_user_with_perms(db_session, ["user:read"])
    permission_id = user.roles[0].permissions[0].id
    key = permission_cache_key(user.id)
    await redis_client.delete(key)
    try:
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 200
        assert await redis_client.get(key) is not None

        resp = await client.delete(f"/api/v1/permissions/{permission_id}")
        assert resp.status_code == 200
        assert await redis_client.get(key) is None
        assert (await client.get("/api/v1/users", headers=_auth(user))).status_code == 403
    finally:
        await redis_client.delete(key)


async def test_redis_failure_falls_back_to_database(
    client, db_session, redis_client
):
    user = await _make_user_with_perms(db_session, ["user:read"])
    key = permission_cache_key(user.id)
    await redis_client.delete(key)

    async def broken_redis():
        return _BrokenRedis()

    app.dependency_overrides[get_redis] = broken_redis
    try:
        resp = await client.get("/api/v1/users", headers=_auth(user))
        assert resp.status_code == 200
    finally:
        async def restore_redis():
            return redis_client

        app.dependency_overrides[get_redis] = restore_redis
        await redis_client.delete(key)


async def test_corrupt_cache_is_treated_as_miss(client, db_session, redis_client):
    user = await _make_user_with_perms(db_session, ["user:read"])
    key = permission_cache_key(user.id)
    await redis_client.set(key, "not-json")
    try:
        resp = await client.get("/api/v1/users", headers=_auth(user))
        assert resp.status_code == 200
        cached = await redis_client.get(key)
        assert cached is not None and cached.startswith("[")
    finally:
        await redis_client.delete(key)
