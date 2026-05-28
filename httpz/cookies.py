from __future__ import annotations

from collections.abc import MutableMapping
from typing import Dict, Iterator, Set


class Cookies(MutableMapping):
    """Cookie container synced from Go bridge response cookies.

    Cookies set explicitly by the user (via the constructor or `client.cookies[k] = v`)
    are tracked so they get re-sent on subsequent requests via a `Cookie:` header.
    Response-set cookies are kept here for visibility but are sent automatically by
    the Go session's cookie jar, so they're not duplicated into the header.
    """

    def __init__(self, cookies=None):
        self._cookies: Dict[str, str] = {}
        self._user_set: Set[str] = set()
        if cookies:
            if isinstance(cookies, dict):
                for k, v in cookies.items():
                    self._cookies[k] = v
                    self._user_set.add(k)
            elif isinstance(cookies, Cookies):
                self._cookies.update(cookies._cookies)
                self._user_set.update(cookies._user_set)

    def __setitem__(self, name: str, value: str):
        self._cookies[name] = value
        self._user_set.add(name)

    def __getitem__(self, name: str) -> str:
        return self._cookies[name]

    def __delitem__(self, name: str):
        del self._cookies[name]
        self._user_set.discard(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self._cookies)

    def __len__(self) -> int:
        return len(self._cookies)

    def __bool__(self) -> bool:
        return len(self._cookies) > 0

    def update_from_response(self, cookies_dict: dict):
        if cookies_dict:
            self._cookies.update(cookies_dict)

    def user_set_items(self) -> Dict[str, str]:
        """Return cookies the caller set explicitly (not those received from responses)."""
        return {k: self._cookies[k] for k in self._user_set if k in self._cookies}

    def __repr__(self):
        return f"Cookies({self._cookies!r})"
