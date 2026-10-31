from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

ModelStatus = Literal["available", "unavailable", "rate_limited"]

# 单个能力标签；拼接后总长度另由校验器限制在数据库列宽 500 以内
Capability = Annotated[str, Field(min_length=1, max_length=50)]


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model_id: str = Field(min_length=1, max_length=100)
    provider_id: int
    capabilities: list[Capability] = []
    context_length: int = Field(default=4096, ge=1)
    input_price: float = Field(default=0, ge=0)
    output_price: float = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=1, max_length=10)
    is_default: bool = False
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("capabilities")
    @classmethod
    def _capabilities_fit_column(cls, values: list[str]) -> list[str]:
        if len(",".join(values)) > 500:
            raise ValueError("capabilities 逗号拼接后不能超过 500 个字符")
        return values


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    capabilities: list[Capability] | None = None
    context_length: int | None = Field(default=None, ge=1)
    status: ModelStatus | None = None
    input_price: float | None = Field(default=None, ge=0)
    output_price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=10)
    is_default: bool | None = None
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("capabilities")
    @classmethod
    def _capabilities_fit_column(cls, values: list[str] | None) -> list[str] | None:
        if values is not None and len(",".join(values)) > 500:
            raise ValueError("capabilities 逗号拼接后不能超过 500 个字符")
        return values


class ModelRead(BaseModel):
    id: int
    name: str
    model_id: str
    provider_id: int
    provider_name: str = ""       # 从关联对象中取
    capabilities: list[str] = []  # 从逗号分隔字符串转换
    context_length: int
    status: str
    input_price: float
    output_price: float
    currency: str
    is_default: bool
    description: str | None

    model_config = {"from_attributes": True}
