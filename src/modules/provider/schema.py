from typing import Literal

from pydantic import BaseModel, Field

ProviderType = Literal["openai", "anthropic", "aliyun", "azure", "local", "custom"]


class ProviderCreate(BaseModel):
    """创建供应商请求"""
    name: str = Field(min_length=1, max_length=100)
    type: ProviderType
    endpoint: str = Field(min_length=1, max_length=500)
    api_key: str | None = None
    description: str | None = Field(default=None, max_length=500)


class ProviderUpdate(BaseModel):
    """更新供应商请求 — 所有字段可选"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: ProviderType | None = None
    endpoint: str | None = Field(default=None, min_length=1, max_length=500)
    api_key: str | None = None
    description: str | None = Field(default=None, max_length=500)


class ProviderRead(BaseModel):
    """供应商响应"""
    id: int
    name: str
    type: str
    status: str
    endpoint: str
    api_key: str | None = None  # 返回时由 Service 解密
    description: str | None
    model_count: int = 0       # 关联模型数量，Service 层计算后填入

    model_config = {"from_attributes": True}    #  Pydantic 可以直接从 SQLAlchemy ORM 对象读取属性
