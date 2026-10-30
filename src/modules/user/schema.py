import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.modules.role.schema import RoleRead


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("密码过长(UTF-8 编码不得超过 72 字节)")
        # if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        #     raise ValueError("密码需同时包含字母和数字")
        return v


class UserRead(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}

class UserWithRolesRead(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    roles: list[RoleRead] = []     # 从 role 模块导入 RoleRead
    model_config = {"from_attributes": True}

class UserAssignRoles(BaseModel):
    role_ids: list[int]