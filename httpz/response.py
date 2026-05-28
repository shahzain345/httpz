from __future__ import annotations

import base64
import json as _json
from typing import Any

from .headers import Headers
from .cookies import Cookies
from .exceptions import HTTPStatusError


class Response:
    """HTTP Response object, modeled after httpx.Response."""

    def __init__(self, bridge_response: dict, request_url: str, request_method: str):
        self.status_code: int = bridge_response["status_code"]
        self.url: str = bridge_response.get("url", request_url)

        # Decode base64 body
        body_b64 = bridge_response.get("body_base64", "")
        self.content: bytes = base64.b64decode(body_b64) if body_b64 else b""

        # Headers
        raw_headers = bridge_response.get("headers", [])
        self.headers = Headers(raw_headers)

        # Cookies
        raw_cookies = bridge_response.get("cookies", {})
        self.cookies = Cookies(raw_cookies)

        # Protocol
        self.http_version: str = bridge_response.get("proto", "")

        # Store request info
        self._request_url = request_url
        self._request_method = request_method

    @property
    def text(self) -> str:
        """Response body decoded as text."""
        return self.content.decode(self.encoding)

    def json(self, **kwargs) -> Any:
        """Parse response body as JSON."""
        return _json.loads(self.content, **kwargs)

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600

    @property
    def encoding(self) -> str:
        content_type = self.headers.get("content-type", "")
        if "charset=" in content_type:
            return content_type.split("charset=")[-1].split(";")[0].strip()
        return "utf-8"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError(
                f"{self.status_code} for url {self.url}",
                response=self,
            )

    def __repr__(self):
        return f"<Response [{self.status_code}]>"
