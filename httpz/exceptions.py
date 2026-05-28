class HTTPZError(Exception):
    """Base exception for all httpz errors."""


class TransportError(HTTPZError):
    """Error communicating with the Go bridge."""


class BridgeError(HTTPZError):
    """Error returned from the Go shared library."""


class TimeoutError(HTTPZError):
    """Request timed out."""


class ProxyError(HTTPZError):
    """Proxy configuration or connection error."""


class TooManyRedirects(HTTPZError):
    """Too many redirects."""


class ConnectionError(HTTPZError):
    """Connection failed."""


class HTTPStatusError(HTTPZError):
    """Raised by Response.raise_for_status() for 4xx/5xx responses."""

    def __init__(self, message: str, *, response):
        self.response = response
        super().__init__(message)
