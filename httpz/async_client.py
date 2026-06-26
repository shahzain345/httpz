"""
httpz.async_client - asyncio-friendly HTTP client.

Copyright (c) 2026 Shahzain345. All rights reserved.
Licensed under the MIT License.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Union

from .response import Response
from .headers import Headers, HeaderTypes
from .cookies import Cookies
from .client import Client


class AsyncClient:
    """
    Asyncio-friendly counterpart to ``httpz.Client``. Mirrors
    ``httpx.AsyncClient`` - same API surface, every I/O method is an
    ``async def`` that you ``await``.

    ``AsyncClient`` is implemented as a thin async wrapper around ``Client``:
    it constructs a sync ``Client`` internally and every request hops into a
    worker thread via ``asyncio.to_thread`` so the blocking CGO call never
    stalls the event loop.

    Note:
        Because each request is dispatched to the asyncio default thread
        pool, async throughput is bounded by that pool's size (typically
        ``min(32, os.cpu_count() + 4)``). For most workloads this is fine,
        but if you are firing hundreds of concurrent requests and don't need
        TLS-fingerprint control, libraries like ``aiohttp`` or ``httpx``'s
        own async client will give you higher event-loop-native throughput.

    Args:
        **kwargs: Forwarded verbatim to ``httpz.Client``. See ``Client``'s
            docstring for the full list (``headers``, ``cookies``, ``proxy``,
            ``ja3``, ``h2_fingerprint``, ``browser``, ``user_agent``,
            ``impersonate``, ``timeout``, ``max_redirects``, ``verify``,
            ``force_http1``).

    Attributes:
        headers (Headers): Shared with the underlying sync client. Mutate
            to add or replace default headers for subsequent requests.
        cookies (Cookies): Shared with the underlying sync client.

    Example:
        Basic usage::

            async with httpz.AsyncClient() as client:
                resp = await client.get("https://example.com")
                print(resp.text)

        Fan out concurrent requests with a Chrome-131 fingerprint::

            import asyncio
            import httpz

            async def main():
                async with httpz.AsyncClient(impersonate="chrome131") as c:
                    urls = [
                        f"https://httpbin.org/anything/{i}"
                        for i in range(20)
                    ]
                    responses = await asyncio.gather(
                        *(c.get(u) for u in urls)
                    )
                    for r in responses:
                        print(r.status_code, r.url)

            asyncio.run(main())
    """

    def __init__(self, **kwargs):
        self._sync = Client(**kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        await asyncio.to_thread(self._sync.close)

    # -- HTTP Methods --

    async def request(self, method: str, url: str, **kwargs) -> Response:
        return await asyncio.to_thread(self._sync.request, method, url, **kwargs)

    async def get(self, url: str, **kwargs) -> Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Response:
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> Response:
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Response:
        return await self.request("DELETE", url, **kwargs)

    async def head(self, url: str, **kwargs) -> Response:
        return await self.request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> Response:
        return await self.request("OPTIONS", url, **kwargs)

    # -- Configuration --

    async def apply_ja3(self, ja3: str, browser: str) -> None:
        await asyncio.to_thread(self._sync.apply_ja3, ja3, browser)

    async def apply_h2_fingerprint(self, fingerprint: str) -> None:
        await asyncio.to_thread(self._sync.apply_h2_fingerprint, fingerprint)

    async def set_proxy(self, proxy_url: str) -> None:
        await asyncio.to_thread(self._sync.set_proxy, proxy_url)

    async def clear_proxy(self) -> None:
        await asyncio.to_thread(self._sync.clear_proxy)

    @property
    def cookies(self) -> Cookies:
        return self._sync.cookies

    @cookies.setter
    def cookies(self, value):
        # Delegate to the sync client's coercing setter so `client.cookies = {...}`
        # (a plain dict) still works.
        self._sync.cookies = value

    @property
    def headers(self) -> Headers:
        return self._sync.headers

    @headers.setter
    def headers(self, value):
        # Delegate to the sync client's coercing setter so `client.headers = {...}`
        # (a plain dict) still works.
        self._sync.headers = value

    def __repr__(self):
        return f"<httpz.AsyncClient [session={self._sync._session_id}]>"
