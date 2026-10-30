import uuid

import pytest
from sqlalchemy import select

from src.modules.permission.model import Permission
from src.modules.role.model import Role
from src.modules.user.model import User
from src.utils.jwt_utils import encode_jwt

pytestmark = pytest.mark.asyncio


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {encode_jwt({'sub': str(user.id)})}"}


async def _make_user(db_session) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"plain_{suffix}",
        email=f"plain_{suffix}@example.com",
        hashed_password="not-used",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _get_or_create_permission(db_session, code: str) -> Permission:
    perm = (
        await db_session.execute(select(Permission).where(Permission.code == code))
    ).scalar_one_or_none()
    if perm is None:
        perm = Permission(code=code, name=f"权限 {code}")
        db_session.add(perm)
        await db_session.flush()
    return perm


async def test_anonymous_rejected(anon_client):
    resp = await anon_client.get("/api/v1/users")

    assert resp.status_code == 401


async def test_user_without_permission_forbidden(client, db_session):
    user = await _make_user(db_session)

    resp = await client.get("/api/v1/users", headers=_auth(user))

    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == 403
    assert "user:read" in body["message"]


async def test_user_with_permission_allowed(client, db_session):
    perm = await _get_or_create_permission(db_session, "user:read")
    suffix = uuid.uuid4().hex[:8]
    role = Role(code=f"reader_{suffix}", name="读角色")
    role.permissions = [perm]
    # 关系在 flush 前赋值，避免 flush 时触发集合懒加载
    user = User(
        username=f"reader_{suffix}",
        email=f"reader_{suffix}@example.com",
        hashed_password="not-used",
        roles=[role],
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.get("/api/v1/users", headers=_auth(user))

    assert resp.status_code == 200
    assert resp.json()["code"] == 200


async def test_disabled_user_rejected(client, db_session):
    user = await _make_user(db_session)
    user.is_active = False
    await db_session.flush()

    resp = await client.get("/api/v1/users/me", headers=_auth(user))

    assert resp.status_code == 401
    assert resp.json()["code"] == 401
