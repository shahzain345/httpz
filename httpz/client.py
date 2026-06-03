"""
httpz.client - synchronous HTTP client.

Copyright (c) 2026 Shahzain345. All rights reserved.
Licensed under the MIT License.
"""
from __future__ import annotations

import base64
import json as _json
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from ._bridge import Bridge
from .response import Response
from .headers import Headers, HeaderTypes
from .cookies import Cookies
from .exceptions import HTTPZError
from .presets import resolve_impersonate
from ._impersonate_headers import default_browser_headers
from ._types import BrowserTypeLiteral


class Client:
    """
    Synchronous, session-scoped HTTP client with first-class TLS-fingerprint
    control. Modeled after ``httpx.Client`` so most existing httpx code ports
    over by changing the import.

    Each ``Client`` owns a session inside the Go-side ``azuretls-client``
    runtime (reached via a thin CGO bridge). That session holds the TLS spec,
    HTTP/2 spec, cookie jar, default headers, proxy, and connection pool, so
    multiple requests through the same client reuse connections and share
    cookie state, exactly like a ``requests.Session`` or ``httpx.Client``.
    When the client is closed (explicitly via ``.close()``, by exiting a
    ``with`` block, or when garbage-collected) the Go-side session is torn
    down and its sockets are released.

    Args:
        headers: Default headers merged into every request. Per-request
            ``headers=`` overrides on a key-by-key basis.
        cookies: Pre-populated cookie jar (``dict`` or ``Cookies``). Cookies
            sent by the server are added automatically.
        proxy: Upstream proxy URL. Schemes: ``http``, ``https``, ``socks5``.
        ja3: JA3 client fingerprint - rewrites the TLS ClientHello to match.
            Requires ``browser=``.
        h2_fingerprint: Akamai-format HTTP/2 fingerprint - controls SETTINGS,
            WINDOW_UPDATE, pseudo-header order, and PRIORITY frames.
        browser: Navigator family that backs the JA3 / HTTP/2 stack. Use the
            module constants: ``httpz.CHROME``, ``FIREFOX``, ``SAFARI``,
            ``EDGE``, ``OPERA``, ``IOS``.
        user_agent: Overrides the default ``User-Agent``.
        impersonate: Shorthand that resolves to a full preset
            (``ja3`` + ``h2_fingerprint`` + ``browser`` + ``user_agent``).
            Any other explicit kwarg you pass still wins over the preset.
        timeout: Default per-request timeout in seconds. Per-request
            ``timeout=`` overrides.
        max_redirects: Maximum redirect-chain length before raising
            ``TooManyRedirects``.
        verify: When ``False``, TLS certificate verification is skipped.
            Useful for self-signed certs in development; never ship ``False``
            to production.
        browser_headers: When ``True`` (default) and a browser navigator is
            active (via ``impersonate=`` or ``browser=``), httpz also sends that
            browser's default request headers — client hints (``sec-ch-ua*``),
            ``Accept``, ``Accept-Language``, ``Sec-Fetch-*``, ``priority`` — so
            the request looks like a real browser at the HTTP layer, not just at
            the TLS/HTTP2 handshake. Anything you pass in ``headers=`` overrides
            these per key. Set ``False`` to send only the headers you specify.

    Attributes:
        headers (Headers): Mutable case-insensitive multi-dict of default
            headers. Set ``client.headers["X-Foo"] = "bar"`` to add or
            replace a default header for subsequent requests.
        cookies (Cookies): The session cookie jar. Read after a response to
            inspect what the server set; mutate to inject your own.

    Raises:
        HTTPZError: If ``ja3`` is supplied without ``browser``, or if a
            request is made after the client has been closed.

    Example:
        Basic usage::

            with httpz.Client() as client:
                resp = client.get("https://example.com")
                print(resp.text)

        With a custom JA3 fingerprint::

            client = httpz.Client(
                ja3="771,4865-4867-...",
                h2_fingerprint="1:65536;...|15663105|0|m,s,a,p",
                browser="chrome",
            )

        Everything together (preset + proxy + per-request timeout)::

            with httpz.Client(
                impersonate="chrome131",
                proxy="socks5://user:pass@127.0.0.1:1080",
                timeout=30.0,
                headers={"Accept-Language": "en-US,en;q=0.9"},
            ) as client:
                client.cookies["session"] = "abc123"
                r = client.get("https://api.example.com/me")
                r.raise_for_status()

                # Rotate the TLS fingerprint mid-session
                client.apply_ja3("771,4865-4867-...", browser="chrome")
                r2 = client.post(
                    "https://api.example.com/items",
                    json={"name": "x"},
                )
    """

    def __init__(
        self,
        *,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[Union[Cookies, Dict[str, str]]] = None,
        proxy: Optional[str] = None,
        ja3: Optional[str] = None,
        h2_fingerprint: Optional[str] = None,
        browser: Optional[str] = None,
        user_agent: Optional[str] = None,
        impersonate: Optional[BrowserTypeLiteral] = None,
        timeout: Optional[float] = None,
        max_redirects: int = 10,
        verify: bool = True,
        browser_headers: bool = True,
    ):
        self._closed = True  # safe default until session is created

        # An impersonate preset is just shorthand for setting ja3 + h2 + browser
        # + user_agent together. Explicit args still win, so callers can pin a
        # preset and then override one piece.
        if impersonate:
            preset = resolve_impersonate(impersonate)
            ja3 = ja3 or preset.get("ja3") or None
            h2_fingerprint = h2_fingerprint or preset.get("h2_fingerprint") or None
            browser = browser or preset.get("browser") or None
            user_agent = user_agent or preset.get("user_agent") or None

        if ja3 and not browser:
            raise HTTPZError(
                "browser is required when using ja3. "
                "Use browser='chrome', 'firefox', or 'safari'."
            )

        self._bridge = Bridge()
        self.cookies = Cookies(cookies) if cookies else Cookies()

        # Build session config
        config: Dict[str, Any] = {}
        if browser:
            config["browser"] = browser
        if timeout:
            config["timeout_ms"] = int(timeout * 1000)
        if max_redirects != 10:
            config["max_redirects"] = max_redirects
        if not verify:
            config["insecure_skip"] = True
        if proxy:
            config["proxy"] = proxy
        if ja3:
            config["ja3"] = ja3
            config["ja3_navigator"] = browser
        if h2_fingerprint:
            config["h2_fingerprint"] = h2_fingerprint

        # When emulating a browser, seed the default request headers that browser
        # always sends (client hints, Accept, Sec-Fetch, ...) so the request
        # matches a real browser at the HTTP layer, not just the TLS/HTTP2
        # handshake. Caller-supplied headers override these per key while keeping
        # the browser's header order; extra caller headers are appended.
        # Public attribute so callers can mutate after construction
        # (e.g. `client.headers["X-Foo"] = "bar"`), matching the httpx API.
        user_headers = Headers(headers) if headers else Headers()
        if browser_headers and browser:
            merged = Headers()
            for k, v in default_browser_headers(browser, user_agent):
                merged[k] = user_headers[k] if k in user_headers else v
            for k, v in user_headers.multi_items():
                if k not in merged:
                    merged[k] = v
            self.headers = merged
        else:
            self.headers = user_headers
        if self.headers:
            config["headers"] = self.headers.to_ordered_pairs()

        # The browser default headers carry User-Agent at its natural position.
        # Only fall back to the separate user_agent config (which the Go layer
        # appends last) when UA isn't already in the ordered headers.
        if user_agent and "user-agent" not in self.headers:
            config["user_agent"] = user_agent

        self._session_id = self._bridge.create_session(config)
        self._closed = False
        self._proxy = proxy
        self._timeout = timeout

    @property
    def headers(self) -> Headers:
        return self._headers

    @headers.setter
    def headers(self, value) -> None:
        # Coerce any assigned value (e.g. a plain dict) into a Headers instance so
        # callers can do `client.headers = {...}` and still get ordered-pair
        # serialization in request().
        self._headers = value if isinstance(value, Headers) else Headers(value)

    @property
    def cookies(self) -> Cookies:
        return self._cookies

    @cookies.setter
    def cookies(self, value) -> None:
        # Coerce any assigned value (e.g. a plain dict) into a Cookies instance so
        # callers can do `client.cookies = {...}` and still get user_set_items()
        # and update_from_response() in request().
        self._cookies = value if isinstance(value, Cookies) else Cookies(value)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        if not self._closed:
            try:
                self.close()
            except Exception:
                pass

    def close(self):
        if not self._closed:
            self._bridge.close_session(self._session_id)
            self._closed = True

    # -- Configuration --

    def apply_ja3(self, ja3: str, browser: str) -> None:
        """Apply a JA3 TLS fingerprint to this session.

        Args:
            ja3: JA3 fingerprint string.
            browser: Browser to emulate ('chrome', 'firefox', 'safari').
        """
        self._bridge.apply_ja3(self._session_id, ja3, browser)

    def apply_h2_fingerprint(self, fingerprint: str) -> None:
        """Apply an HTTP/2 (Akamai) fingerprint to this session."""
        self._bridge.apply_h2_fingerprint(self._session_id, fingerprint)

    def set_proxy(self, proxy_url: str) -> None:
        """Set proxy for this session. Supports http, https, socks5."""
        self._bridge.set_proxy(self._session_id, proxy_url)
        self._proxy = proxy_url

    def clear_proxy(self) -> None:
        """Remove proxy from this session."""
        self._bridge.clear_proxy(self._session_id)
        self._proxy = None

    # -- HTTP Methods --

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[HeaderTypes] = None,
        content: Optional[bytes] = None,
        data: Optional[Union[dict, str, bytes]] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
        max_redirects: Optional[int] = None,
    ) -> Response:
        """Send an HTTP request."""
        if self._closed:
            raise HTTPZError("Client is closed")

        # Build URL with query params
        if params:
            parsed = urlparse(url)
            existing = parse_qs(parsed.query)
            existing.update({k: [v] for k, v in params.items()})
            new_query = urlencode({k: v[0] for k, v in existing.items()})
            url = urlunparse(parsed._replace(query=new_query))

        req_data: Dict[str, Any] = {
            "method": method.upper(),
            "url": url,
        }

        # Merge default headers with per-request headers, plus any user-set cookies.
        merged = self.headers.copy() if self.headers else Headers()
        if headers:
            request_headers = Headers(headers)
            for k, v in request_headers.multi_items():
                merged[k] = v

        # User-set cookies (not those received from responses — the Go session jar
        # handles re-sending those) get serialized into a Cookie header.
        user_cookies = self.cookies.user_set_items()
        if user_cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in user_cookies.items())
            existing = merged.get("cookie")
            merged["cookie"] = f"{existing}; {cookie_str}" if existing else cookie_str

        if merged:
            req_data["headers"] = merged.to_ordered_pairs()

        # Body handling
        if json is not None:
            req_data["body"] = _json.dumps(json)
            req_data["content_type"] = "application/json"
        elif data is not None:
            if isinstance(data, dict):
                req_data["body"] = urlencode(data)
                req_data["content_type"] = "application/x-www-form-urlencoded"
            elif isinstance(data, bytes):
                req_data["body_base64"] = base64.b64encode(data).decode()
            else:
                req_data["body"] = str(data)
        elif content is not None:
            req_data["body_base64"] = base64.b64encode(content).decode()

        # Timeout
        effective_timeout = timeout if timeout is not None else self._timeout
        if effective_timeout:
            req_data["timeout_ms"] = int(effective_timeout * 1000)

        # Redirects
        if not follow_redirects:
            req_data["disable_redirect"] = True
        if max_redirects is not None:
            req_data["max_redirects"] = max_redirects

        # Execute
        raw_response = self._bridge.request(self._session_id, req_data)
        response = Response(raw_response, request_url=url, request_method=method)

        # Sync cookies
        self.cookies.update_from_response(response.cookies._cookies)

        return response

    def get(self, url: str, **kwargs) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs) -> Response:
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def __repr__(self):
        return f"<httpz.Client [session={self._session_id}]>"
