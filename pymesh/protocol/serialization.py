"""
Serialization helpers for PyMesh protocol messages.
"""

import json
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def serialize_message(model: BaseModel) -> bytes:
    return model.model_dump_json().encode("utf-8")


def deserialize_message(data: bytes, model_cls: Type[T]) -> T:
    return model_cls.model_validate_json(data.decode("utf-8"))
