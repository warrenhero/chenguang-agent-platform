from src.core.deps import require_permission
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_schema import PageResult, ResponseSchema
from src.core.deps import PageParams
from src.infra.database import get_db
from src.modules.permission.schema import PermissionRead
from src.modules.role.schema import (
    RoleAssignPermissions,
    RoleCreate,
    RoleRead,
    RoleUpdate,
)
from src.modules.role.service import RoleService

router = APIRouter(prefix="/roles", tags=["Role"])


def get_role_service(db: AsyncSession = Depends(get_db)) -> RoleService:
    return RoleService(db)


# POST  /api/v1/roles   创建角色
@router.post(
    "",
    response_model=ResponseSchema[RoleRead],
    summary="创建角色",
    dependencies=[Depends(require_permission("role:create"))],
)
async def create_role(
    role: RoleCreate,
    service: RoleService = Depends(get_role_service),
):
    data = await service.create_role(role)
    return ResponseSchema[RoleRead](data=RoleRead.model_validate(data))


# GET   /api/v1/roles   角色列表
@router.get(
    "",
    response_model=ResponseSchema[list[RoleRead]],
    summary="获取角色列表",
    dependencies=[Depends(require_permission("role:read"))],
)
async def get_roles(service: RoleService = Depends(get_role_service)):
    data = await service.list_roles()
    return ResponseSchema[list[RoleRead]](
        data=[RoleRead.model_validate(r) for r in data]
    )


# GET  /api/v1/permissions/search?page=1&size=10&keyword=xxx
@router.get(
    "/search",
    response_model=ResponseSchema[PageResult[RoleRead]],
    summary="分页搜索角色",
    dependencies=[Depends(require_permission("role:read"))],
)
async def list_search_result(
    params: PageParams = Depends(),
    svc: RoleService = Depends(get_role_service),
):
    """分页搜索权限"""
    roles, total_count = await svc.search_page(
        offset=params.offset, limit=params.page_size, keyword=params.keyword
    )
    return ResponseSchema(
        data=PageResult(
            items=[RoleRead.model_validate(r) for r in roles],
            total=total_count,
            page=params.page,
            page_size=params.page_size,
        )
    )


# GET   /api/v1/roles/{role_id} 角色详情（含权限列表）
@router.get(
    "/{role_id}",
    response_model=ResponseSchema[RoleRead],
    summary="获取角色详情",
    dependencies=[Depends(require_permission("role:read"))],
)
async def get_role(role_id: int, service: RoleService = Depends(get_role_service)):
    data = await service.get_role(role_id)
    permissions = [PermissionRead.model_validate(p) for p in data.permissions]

    rd = RoleRead.model_validate(data)
    rd.permissions = permissions
    return ResponseSchema[RoleRead](data=rd)


# PUT   /api/v1/roles/{role_id} 更新角色
@router.put(
    "/{role_id}",
    response_model=ResponseSchema[RoleRead],
    summary="更新角色",
    dependencies=[Depends(require_permission("role:update"))],
)
async def update_role(
    role_id: int,
    role: RoleUpdate,
    service: RoleService = Depends(get_role_service),
):
    data = await service.update_role(role_id, role)
    return ResponseSchema[RoleRead](data=RoleRead.model_validate(data))


# DELETE    /api/v1/roles/{role_id} 删除角色
@router.delete(
    "/{role_id}",
    response_model=ResponseSchema[None],
    summary="删除角色",
    dependencies=[Depends(require_permission("role:delete"))],
)
async def delete_role(
    role_id: int,
    service: RoleService = Depends(get_role_service),
):
    await service.delete_role(role_id)
    return ResponseSchema[None](data=None)


# PUT   /api/v1/roles/{role_id}/permissions 给角色分配权限
@router.put(
    "/{role_id}/permissions",
    response_model=ResponseSchema[RoleRead],
    summary="给角色分配权限",
    dependencies=[Depends(require_permission("role:assign"))]
)
async def update_role_permissions(
    role_id: int,
    role_permissions: RoleAssignPermissions,
    service: RoleService = Depends(get_role_service),
):
    data = await service.assign_permissions(role_id, role_permissions.permission_ids)
    return ResponseSchema[RoleRead](data=RoleRead.model_validate(data))
