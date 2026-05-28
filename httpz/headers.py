from __future__ import annotations

from collections.abc import MutableMapping
from typing import Iterator, List, Tuple, Union


HeaderTypes = Union[
    "Headers",
    dict,
    List[Tuple[str, str]],
    List[List[str]],
]


class Headers(MutableMapping):
    """HTTP headers with preserved insertion order and case-insensitive lookup."""

    def __init__(self, headers=None):
        self._list: List[Tuple[str, str]] = []
        if headers is not None:
            if isinstance(headers, Headers):
                self._list = list(headers._list)
            elif isinstance(headers, dict):
                for k, v in headers.items():
                    self._list.append((str(k), str(v)))
            elif isinstance(headers, (list, tuple)):
                for item in headers:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        self._list.append((str(item[0]), str(item[1])))

    def __getitem__(self, key: str) -> str:
        key_lower = key.lower()
        for k, v in self._list:
            if k.lower() == key_lower:
                return v
        raise KeyError(key)

    def __setitem__(self, key: str, value: str) -> None:
        key_lower = key.lower()
        self._list = [(k, v) for k, v in self._list if k.lower() != key_lower]
        self._list.append((key, str(value)))

    def __delitem__(self, key: str) -> None:
        key_lower = key.lower()
        original = len(self._list)
        self._list = [(k, v) for k, v in self._list if k.lower() != key_lower]
        if len(self._list) == original:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        seen = set()
        for k, _ in self._list:
            kl = k.lower()
            if kl not in seen:
                seen.add(kl)
                yield k

    def __len__(self) -> int:
        return len(set(k.lower() for k, _ in self._list))

    def __contains__(self, key) -> bool:
        key_lower = key.lower()
        return any(k.lower() == key_lower for k, _ in self._list)

    def __bool__(self) -> bool:
        return len(self._list) > 0

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def get_list(self, key: str) -> List[str]:
        """Get all values for a header (multi-value support)."""
        key_lower = key.lower()
        return [v for k, v in self._list if k.lower() == key_lower]

    def to_ordered_pairs(self) -> List[List[str]]:
        """Convert to the JSON format expected by the Go bridge."""
        return [[k, v] for k, v in self._list]

    def multi_items(self) -> List[Tuple[str, str]]:
        """Return all (key, value) pairs including duplicates."""
        return list(self._list)

    def copy(self) -> "Headers":
        h = Headers()
        h._list = list(self._list)
        return h

    def __repr__(self):
        return f"Headers({dict(self._list)})"
