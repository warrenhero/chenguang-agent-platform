import uuid

import pytest
from sqlalchemy import select

from src.core.bootstrap import (
    ADMIN_ROLE_CODE,
    DEFAULT_PERMISSIONS,
    apply_rbac_seed,
)
from src.modules.permission.model import Permission
from src.modules.role.model import Role
from src.modules.user.model import User

pytestmark = pytest.mark.asyncio


async def test_bootstrap_creates_permissions_and_admin_role(db_session):
    await apply_rbac_seed(db_session)

    codes = {
        p.code
        for p in (await db_session.execute(select(Permission))).scalars().all()
    }
    assert {code for code, _, _ in DEFAULT_PERMISSIONS} <= codes

    admin = (
        await db_session.execute(select(Role).where(Role.code == ADMIN_ROLE_CODE))
    ).scalar_one()
    assert {p.code for p in admin.permissions} >= {
        code for code, _, _ in DEFAULT_PERMISSIONS
    }


async def test_bootstrap_is_idempotent(db_session):
    await apply_rbac_seed(db_session)
    await apply_rbac_seed(db_session)

    permissions = (await db_session.execute(select(Permission))).scalars().all()
    assert len(permissions) == len({p.code for p in permissions})

    admin_roles = (
        await db_session.execute(select(Role).where(Role.code == ADMIN_ROLE_CODE))
    ).scalars().all()
    assert len(admin_roles) == 1


async def test_bootstrap_creates_superuser(db_session):
    suffix = uuid.uuid4().hex[:8]
    username = f"bootstrap_{suffix}"

    await apply_rbac_seed(
        db_session,
        superuser_username=username,
        superuser_password="Abc@123456",
        superuser_email=f"{username}@example.com",
    )

    user = (
        await db_session.execute(select(User).where(User.username == username))
    ).scalar_one()
    assert user.is_superuser is True
    assert user.is_active is True
