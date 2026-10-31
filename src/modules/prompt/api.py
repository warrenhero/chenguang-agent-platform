from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.infra.database import get_db
from src.core.base_schema import ResponseSchema, PageResult
from src.core.deps import PageParams, get_current_user, require_permission
from src.modules.prompt.schema import (
    PromptCreate, PromptUpdate, PromptRead,
    PromptVersionRead, PublishRequest, RollbackRequest,
)
from src.modules.prompt.service import PromptService
from src.modules.user.model import User

router = APIRouter(prefix="/prompts", tags=["Prompt管理"])


def get_prompt_service(db: AsyncSession = Depends(get_db)) -> PromptService:
    return PromptService(db)


@router.post(
    "",
    response_model=ResponseSchema[PromptRead],
    summary="创建Prompt",
    dependencies=[Depends(require_permission("prompt:create"))],
)
async def create_prompt(
    data: PromptCreate,
    current_user: User = Depends(get_current_user),
    svc: PromptService = Depends(get_prompt_service),
):
    result = await svc.create_prompt(data, current_user.username)
    return ResponseSchema(data=result)


@router.get(
    "",
    response_model=ResponseSchema[PageResult[PromptRead]],
    summary="Prompt列表",
    dependencies=[Depends(require_permission("prompt:read"))],
)
async def list_prompts(
    params: PageParams = Depends(),
    svc: PromptService = Depends(get_prompt_service),
):
    page_result = await svc.list_prompts(params)
    return ResponseSchema(data=page_result)


@router.get(
    "/{prompt_id}",
    response_model=ResponseSchema[PromptRead],
    summary="Prompt详情",
    dependencies=[Depends(require_permission("prompt:read"))],
)
async def get_prompt(
    prompt_id: int,
    svc: PromptService = Depends(get_prompt_service),
):
    result = await svc.get_prompt(prompt_id)
    return ResponseSchema(data=result)


@router.put(
    "/{prompt_id}",
    response_model=ResponseSchema[PromptRead],
    summary="更新Prompt",
    dependencies=[Depends(require_permission("prompt:update"))],
)
async def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    svc: PromptService = Depends(get_prompt_service),
):
    result = await svc.update_prompt(prompt_id, data)
    return ResponseSchema(data=result)


@router.delete(
    "/{prompt_id}",
    response_model=ResponseSchema,
    summary="删除Prompt",
    dependencies=[Depends(require_permission("prompt:delete"))],
)
async def delete_prompt(
    prompt_id: int,
    svc: PromptService = Depends(get_prompt_service),
):
    await svc.delete_prompt(prompt_id)
    return ResponseSchema(message="删除成功")


@router.post(
    "/{prompt_id}/publish",
    response_model=ResponseSchema[PromptRead],
    summary="发布新版本",
    dependencies=[Depends(require_permission("prompt:update"))],
)
async def publish_prompt(
    prompt_id: int,
    data: PublishRequest,
    current_user: User = Depends(get_current_user),
    svc: PromptService = Depends(get_prompt_service),
):
    result = await svc.publish(prompt_id, data, current_user.username)
    return ResponseSchema(data=result)


@router.get(
    "/{prompt_id}/versions",
    response_model=ResponseSchema[list[PromptVersionRead]],
    summary="版本列表",
    dependencies=[Depends(require_permission("prompt:read"))],
)
async def get_versions(
    prompt_id: int,
    svc: PromptService = Depends(get_prompt_service),
):
    results = await svc.get_versions(prompt_id)
    return ResponseSchema(data=results)


@router.post(
    "/{prompt_id}/rollback",
    response_model=ResponseSchema[PromptRead],
    summary="回滚版本",
    dependencies=[Depends(require_permission("prompt:update"))],
)
async def rollback_prompt(
    prompt_id: int,
    data: RollbackRequest,
    svc: PromptService = Depends(get_prompt_service),
):
    result = await svc.rollback(prompt_id, data)
    return ResponseSchema(data=result)
