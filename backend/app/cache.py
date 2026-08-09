"""Small in-memory TTL cache for repeated classification requests."""

from __future__ import annotations

from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        if self.ttl_seconds <= 0:
            return None

        item = self._items.get(key)
        if item is None:
            return None

        expires_at, value = item
        if expires_at <= monotonic():
            self._items.pop(key, None)
            return None

        return value

    def set(self, key: str, value: T) -> None:
        if self.ttl_seconds <= 0:
            return

        self._items[key] = (monotonic() + self.ttl_seconds, value)

    def clear(self) -> None:
        self._items.clear()
