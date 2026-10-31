from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.permission.model import Permission
from src.modules.role.model import Role
from src.modules.user.model import User
from src.utils.password_utils import hash_password_async

# 接口中使用的全部权限编码；新增受保护接口时同步补充
DEFAULT_PERMISSIONS: list[tuple[str, str, str]] = [
    ("user:read", "用户读取", "查看用户与用户角色"),
    ("user:create", "用户创建", "创建用户"),
    ("user:assign", "用户分配角色", "给用户分配角色"),
    ("user:delete", "用户删除", "删除用户"),
    ("role:read", "角色读取", "查看角色"),
    ("role:create", "角色创建", "创建角色"),
    ("role:update", "角色更新", "更新角色"),
    ("role:delete", "角色删除", "删除角色"),
    ("role:assign", "角色分配权限", "给角色分配权限"),
    ("permission:read", "权限读取", "查看权限"),
    ("permission:create", "权限创建", "创建权限"),
    ("permission:update", "权限更新", "更新权限"),
    ("permission:delete", "权限删除", "删除权限"),
    ("provider:read", "供应商读取", "查看供应商"),
    ("provider:create", "供应商创建", "创建供应商"),
    ("provider:update", "供应商更新", "更新供应商与测试连接"),
    ("provider:delete", "供应商删除", "删除供应商"),
    ("model:read", "模型读取", "查看模型"),
    ("model:create", "模型创建", "添加模型"),
    ("model:update", "模型更新", "更新模型"),
    ("model:delete", "模型删除", "删除模型"),
    ("prompt:read", "Prompt读取", "查看 Prompt 与版本"),
    ("prompt:create", "Prompt创建", "创建 Prompt"),
    ("prompt:update", "Prompt更新", "更新、发布与回滚 Prompt"),
    ("prompt:delete", "Prompt删除", "删除 Prompt"),
]

ADMIN_ROLE_CODE = "admin"


async def apply_rbac_seed(
    db: AsyncSession,
    superuser_username: str = "",
    superuser_password: str = "",
    superuser_email: str = "",
) -> None:
    """幂等地初始化 RBAC 基础数据（不提交事务）。

    - 补齐接口使用的权限编码
    - 创建/更新 admin 角色并绑定全部权限
    - 按环境变量创建初始超级管理员（已存在则提升为超级管理员）
    """
    existing = {
        p.code: p
        for p in (await db.execute(select(Permission))).scalars().all()
    }
    for code, name, description in DEFAULT_PERMISSIONS:
        if code not in existing:
            db.add(Permission(code=code, name=name, description=description))
    await db.flush()

    permissions = (await db.execute(select(Permission))).scalars().all()

    admin_role = (
        await db.execute(
            select(Role)
            .where(Role.code == ADMIN_ROLE_CODE)
            .options(selectinload(Role.permissions))
        )
    ).scalar_one_or_none()
    if admin_role is None:
        # 新建时直接带上权限，避免 flush 后再赋值触发异步环境下的懒加载
        admin_role = Role(
            code=ADMIN_ROLE_CODE,
            name="超级管理员",
            description="拥有全部权限",
            permissions=list(permissions),
        )
        db.add(admin_role)
        await db.flush()
    else:
        admin_role.permissions = list(permissions)

    if superuser_username and superuser_password:
        user = (
            await db.execute(select(User).where(User.username == superuser_username))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                username=superuser_username,
                email=superuser_email or f"{superuser_username}@localhost",
                hashed_password=await hash_password_async(superuser_password),
                is_superuser=True,
            )
            db.add(user)
            logger.info(f"已创建初始超级管理员: {superuser_username}")
        elif not user.is_superuser:
            user.is_superuser = True
            user.is_active = True
            logger.info(f"已提升为超级管理员: {superuser_username}")

    logger.info(f"RBAC 初始化完成，权限数: {len(permissions)}")


async def bootstrap_rbac(
    db: AsyncSession,
    superuser_username: str = "",
    superuser_password: str = "",
    superuser_email: str = "",
) -> None:
    """应用启动时调用：初始化 RBAC 种子并提交。"""
    await apply_rbac_seed(
        db,
        superuser_username=superuser_username,
        superuser_password=superuser_password,
        superuser_email=superuser_email,
    )
    await db.commit()
