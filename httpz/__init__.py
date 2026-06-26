"""
httpz - HTTP client with TLS fingerprint control.

Backed by azuretls-client (Go) via shared library.

By Shahzain345
"""

__title__ = "httpz"
__version__ = "0.1.3"

from .client import Client
from .async_client import AsyncClient
from .response import Response
from .headers import Headers
from .cookies import Cookies
from .presets import list_impersonate_targets, resolve_impersonate
from ._types import BrowserTypeLiteral
from .exceptions import (
    HTTPZError,
    TransportError,
    BridgeError,
    TimeoutError,
    ProxyError,
    TooManyRedirects,
    ConnectionError,
    HTTPStatusError,
)

# Browser constants (match azuretls)
CHROME = "chrome"
FIREFOX = "firefox"
SAFARI = "safari"
EDGE = "edge"
OPERA = "opera"
IOS = "ios"


# Module-level convenience functions
def get(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.get(url, **kwargs)


def post(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.post(url, **kwargs)


def put(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.put(url, **kwargs)


def patch(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.patch(url, **kwargs)


def delete(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.delete(url, **kwargs)


def head(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.head(url, **kwargs)


def options(url: str, **kwargs) -> Response:
    with Client() as client:
        return client.options(url, **kwargs)


__all__ = [
    "Client",
    "AsyncClient",
    "Response",
    "Headers",
    "Cookies",
    "HTTPZError",
    "TransportError",
    "BridgeError",
    "TimeoutError",
    "ProxyError",
    "TooManyRedirects",
    "ConnectionError",
    "HTTPStatusError",
    "CHROME",
    "FIREFOX",
    "SAFARI",
    "EDGE",
    "OPERA",
    "IOS",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "list_impersonate_targets",
    "resolve_impersonate",
    "BrowserTypeLiteral",
]
