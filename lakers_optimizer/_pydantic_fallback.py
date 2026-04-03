from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional

_sentinel = object()


class FieldInfo:
    def __init__(self, *, default: Any = _sentinel, default_factory: Optional[Callable[[], Any]] = None) -> None:
        self.default = default
        self.default_factory = default_factory


def Field(*, default: Any = _sentinel, default_factory: Optional[Callable[[], Any]] = None) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory)


class ModelValidator:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def __call__(self, func: Callable) -> Callable:
        setattr(func, "_pydantic_model_validator", self)
        return func


def model_validator(*, mode: str) -> Callable[[Callable], Callable]:
    return ModelValidator(mode)


class BaseModelMeta(type):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: Dict[str, Any]) -> type:
        validators: List[Callable] = []
        for attr_val in namespace.values():
            if hasattr(attr_val, "_pydantic_model_validator"):
                validators.append(attr_val)
        namespace["_pydantic_validators"] = validators
        return super().__new__(mcs, name, bases, namespace)


class BaseModel(metaclass=BaseModelMeta):
    def __init__(self, **kwargs: Any) -> None:
        annotations = getattr(self.__class__, "__annotations__", {})
        for name in annotations:
            if name in kwargs:
                value = kwargs.pop(name)
            else:
                class_attr = getattr(self.__class__, name, _sentinel)
                if isinstance(class_attr, FieldInfo):
                    if class_attr.default_factory is not None:
                        value = class_attr.default_factory()
                    else:
                        value = class_attr.default if class_attr.default is not _sentinel else None
                elif class_attr is not _sentinel:
                    value = class_attr
                else:
                    value = None
            setattr(self, name, value)
        for extra_name, extra_value in kwargs.items():
            setattr(self, extra_name, extra_value)
        self._run_validators()

    def _run_validators(self) -> None:
        for validator in getattr(self.__class__, "_pydantic_validators", []):
            validator(self)

    def model_dump(self) -> Dict[str, Any]:
        annotations = getattr(self.__class__, "__annotations__", {})
        return {name: getattr(self, name) for name in annotations}

    def model_copy(self, deep: bool = False) -> "BaseModel":
        data = self.model_dump()
        if deep:
            data = deepcopy(data)
        return self.__class__(**data)
