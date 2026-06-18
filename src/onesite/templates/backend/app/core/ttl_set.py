"""TTLSet -- a set-like collection where elements expire after a configurable duration."""

import time
from typing import Hashable, Optional


class TTLSet:
    """A set of hashable elements with per-element time-to-live.

    Elements are automatically evicted when their TTL expires.
    Expired entries are cleaned up lazily on every operation.

    Usage::

        cache = TTLSet(ttl=60)          # default 60s TTL
        cache.add("key1")
        cache.add("key2", ttl=10)       # override TTL for this item

        "key1" in cache                  # True  (not expired)
        cache.has("key1")                # True  (same as ``in``)
        len(cache)                       # number of live elements
        cache.remove("key1")             # explicit removal
        cache.clear()                    # remove all
    """

    __slots__ = ("_default_ttl", "_data")

    def __init__(self, ttl: float = 60.0) -> None:
        if ttl <= 0:
            raise ValueError(f"TTL must be positive, got {ttl}")
        self._default_ttl: float = ttl
        # item -> expire_ts (monotonic clock)
        self._data: dict[Hashable, float] = {}

    # ── public API ────────────────────────────────────────────────────

    def set_default_ttl(self, seconds: float) -> None:
        """Change the default TTL for future :meth:`add` calls."""
        if seconds <= 0:
            raise ValueError(f"TTL must be positive, got {seconds}")
        self._default_ttl = seconds

    def add(self, item: Hashable, ttl: Optional[float] = None) -> None:
        """Add *item* with an optional per-item TTL override."""
        effective_ttl = ttl if ttl is not None and ttl > 0 else self._default_ttl
        self._evict_expired()
        self._data[item] = time.monotonic() + effective_ttl

    def remove(self, item: Hashable) -> bool:
        """Remove *item*. Return ``True`` if it existed and was removed."""
        self._evict_expired()
        if item in self._data:
            del self._data[item]
            return True
        return False

    def has(self, item: Hashable) -> bool:
        """Return ``True`` if *item* exists and has not expired."""
        self._evict_expired()
        return item in self._data

    def clear(self) -> None:
        """Remove all elements."""
        self._data.clear()

    # ── dunder methods ────────────────────────────────────────────────

    def __contains__(self, item: object) -> bool:
        self._evict_expired()
        return item in self._data

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._data)

    def __bool__(self) -> bool:
        self._evict_expired()
        return bool(self._data)

    def __repr__(self) -> str:
        return f"TTLSet(ttl={self._default_ttl}, size={len(self)})"

    # ── internal ──────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        """Remove all entries whose TTL has passed."""
        now = time.monotonic()
        expired = [item for item, expire_ts in self._data.items() if expire_ts <= now]
        for item in expired:
            del self._data[item]


# ── module-level singleton ────────────────────────────────────────────

ttl_set = TTLSet()


def set_ttl(seconds: float) -> None:
    """Change the default TTL of the global :data:`ttl_set` instance."""
    ttl_set.set_default_ttl(seconds)
