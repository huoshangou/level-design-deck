"""SpecStore ABC + dataclass + 异常体系。

Phase 4 可加 RemoteSpecStore / NamespacedFileStore 等实现，签名不变。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SpecInfo:
    id: str
    module: str | None
    level_id: str | None
    mtime: float


@dataclass
class SpecRecord:
    id: str
    content: dict[str, Any]
    mtime: float
    module: str | None
    level_id: str | None


@dataclass
class SaveResult:
    id: str
    mtime: float


class SpecStoreError(Exception):
    pass


class SpecNotFound(SpecStoreError):
    pass


class SpecInvalid(SpecStoreError):
    pass


class SpecStore(ABC):
    @abstractmethod
    def list(self, namespace: str = "default") -> list[SpecInfo]: ...

    @abstractmethod
    def get(self, spec_id: str, namespace: str = "default") -> SpecRecord: ...

    @abstractmethod
    def save(self, spec_id: str, content: dict[str, Any], namespace: str = "default") -> SaveResult: ...

    @abstractmethod
    def delete(self, spec_id: str, namespace: str = "default") -> None: ...
