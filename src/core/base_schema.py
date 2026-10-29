from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):  # noqa: UP046
    code: int = 200
    message: str = "success"
    data: Optional[T] = None  # noqa: UP045

class PageResult(BaseModel, Generic[T]):
    """分页结果包装"""
    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    
    # 分页接口返回类型 ResponseSchema[PageResult[UserRead]]