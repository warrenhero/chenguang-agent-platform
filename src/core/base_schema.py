from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):  # noqa: UP046
    code: int = 200
    message: str = "success"
    data: Optional[T] = None  # noqa: UP045
