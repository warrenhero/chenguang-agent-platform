from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_schema import PageResult, ResponseSchema
from src.core.deps import PageParams, get_current_user, require_permission
from src.infra.database import get_db
from src.modules.user.model import User
from src.modules.user.schema import (
    UserAssignRoles,
    UserCreate,
    UserRead,
    UserWithRolesRead,
)
from src.modules.user.service import UserService

router = APIRouter(prefix="/users", tags=["User"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:  # noqa: B008
    return UserService(db)


@router.post(
    "",
    response_model=ResponseSchema[UserRead],
    summary="创建用户",
    dependencies=[Depends(require_permission("user:create"))],
)
async def create_user(
    data: UserCreate,
    svc: UserService = Depends(get_user_service),  # noqa: B008
):
    user = await svc.create_user(data)
    return ResponseSchema(data=UserRead.model_validate(user))


# GET  /api/v1/permissions/search?page=1&size=10&keyword=xxx
@router.get(
    "/search",
    response_model=ResponseSchema[PageResult[UserRead]],
    summary="分页搜索用户",
    dependencies=[Depends(require_permission("user:read"))],
)
async def list_search_result(
    params: PageParams = Depends(),
    svc: UserService = Depends(get_user_service),
):
    """分页搜索权限"""
    users, total_count = await svc.search_page(
        offset=params.offset, limit=params.page_size, keyword=params.keyword
    )
    return ResponseSchema(
        data=PageResult(
            items=[UserRead.model_validate(u) for u in users],
            total=total_count,
            page=params.page,
            page_size=params.page_size,
        )
    )


@router.get(
    "/me", response_model=ResponseSchema[UserRead], summary="获取当前登录用户信息"
)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息(需要 token)"""
    return ResponseSchema(data=UserRead.model_validate(current_user))


@router.get(
    "/{user_id}",
    response_model=ResponseSchema[UserRead],
    summary="获取用户信息",
    dependencies=[Depends(require_permission("user:read"))],
)
async def get_user(
    user_id: int,
    svc: UserService = Depends(get_user_service),  # noqa: B008
):
    user = await svc.get_user(user_id)
    return ResponseSchema(data=UserRead.model_validate(user))


@router.get(
    "",
    response_model=ResponseSchema[list[UserRead]],
    summary="获取用户列表",
    dependencies=[Depends(require_permission("user:read"))],
)
async def list_users(
    offset: int = 0,
    limit: int = 100,
    svc: UserService = Depends(get_user_service),  # noqa: B008
):
    users = await svc.list_users(offset, limit)
    return ResponseSchema(data=[UserRead.model_validate(u) for u in users])


# PUT   /api/v1/users/{user_id}/roles   给用户分配角色
@router.put(
    "/{user_id}/roles",
    response_model=ResponseSchema[UserRead],
    summary="给用户分配角色",
    dependencies=[Depends(require_permission("user:assign"))],
)
async def assign_roles_to_user(
    user_id: int,
    role_ids: UserAssignRoles,
    svc: UserService = Depends(get_user_service),
):
    user = await svc.assign_roles(user_id, role_ids.role_ids)
    return ResponseSchema(data=UserRead.model_validate(user))


@router.delete(
    "/{user_id}", 
    response_model=ResponseSchema[None], 
    summary="删除用户",
    dependencies=[Depends(require_permission("user:delete"))]
    )
async def delete_user(
    user_id: int,
    svc: UserService = Depends(get_user_service),  # noqa: B008
):
    await svc.delete_user(user_id)
    return ResponseSchema()


# GET   /api/v1/users/{user_id}/roles   查看用户的角色列表
@router.get(
    "/{user_id}/roles",
    response_model=ResponseSchema[list[UserWithRolesRead]],
    summary="查看用户的角色列表",
    dependencies=[Depends(require_permission("user:read"))]
)
async def get_user_roles(
    user_id: int,
    svc: UserService = Depends(get_user_service),
):
    user = await svc.get_user_with_roles(user_id)
    return ResponseSchema(data=[UserWithRolesRead.model_validate(user)])
