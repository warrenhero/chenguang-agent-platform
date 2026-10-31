from pydantic import BaseModel, Field
from datetime import datetime


class PromptVariableSchema(BaseModel):
    """Prompt 变量定义"""
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(default="string", min_length=1, max_length=50)  # string / number / boolean / text
    description: str = Field(default="", max_length=500)
    default_value: str | None = None
    required: bool = True


class PromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    category: str = Field(default="general", min_length=1, max_length=50)
    tags: list[str] = []
    content: str = Field(min_length=1)
    variables: list[PromptVariableSchema] = []


class PromptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    tags: list[str] | None = None
    content: str | None = Field(default=None, min_length=1)
    variables: list[PromptVariableSchema] | None = None


class PromptRead(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    tags: list[str]
    content: str
    variables: list[PromptVariableSchema]
    version: str
    status: str
    created_by: str | None

    model_config = {"from_attributes": True}


class PromptVersionRead(BaseModel):
    id: int
    prompt_id: int
    version: str
    content: str
    changelog: str | None
    is_current: bool
    published_by: str | None
    published_at: datetime | None

    model_config = {"from_attributes": True}


class PublishRequest(BaseModel):
    """发布请求"""
    changelog: str = Field(default="", max_length=500)


class RollbackRequest(BaseModel):
    """回滚请求"""
    version: str    # 要回滚到的版本号，如 v1.2

    # 拒绝旧的 {"version_id": ...} 请求体，避免静默忽略后误判为目标版本缺失
    model_config = {"extra": "forbid"}
