"""Default request headers per browser family for ``impersonate=`` / ``browser=``.

When you impersonate a browser, httpz copies the TLS + HTTP/2 fingerprint and the
User-Agent. But a real browser also sends a recognizable set of *request headers*
— client hints (``sec-ch-ua*``), ``Accept``, ``Accept-Language``, ``Sec-Fetch-*``,
``priority`` — and without them a request with a perfect TLS handshake is still
trivially flagged as non-browser (it's missing the headers Chrome/Firefox/Safari
always send). Libraries like ``curl_cffi`` add those headers for you; this module
reconstructs the same set so httpz matches a real browser at the HTTP layer too.

Header *values* that depend on version/platform (the Chromium client hints) are
derived from the User-Agent string. The header *order* mirrors the order each
browser emits for a top-level navigation GET. Anything the caller passes in
``headers=`` overrides these per key (and keeps the browser's header position).
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# curl_cffi-style GREASE brand. Real Chrome randomizes the label/version, but a
# fixed modern value is what the impersonation libraries emit and is widely
# accepted by client-hint parsers.
_NOT_A_BRAND = '"Not-A.Brand";v="24"'

# zstd Accept-Encoding shipped in Chromium 123. Older builds advertise br only.
_ZSTD_SINCE = 123


def _major(ua: str, token: str) -> Optional[int]:
    m = re.search(rf"{re.escape(token)}/(\d+)", ua or "")
    return int(m.group(1)) if m else None


def _platform(ua: str) -> Tuple[str, bool]:
    """Return (``sec-ch-ua-platform`` value, is_mobile) inferred from the UA."""
    u = ua or ""
    if "Android" in u:
        return '"Android"', True
    if "iPhone" in u or "iPad" in u:
        return '"iOS"', True
    if "Windows" in u:
        return '"Windows"', False
    if "Macintosh" in u or "Mac OS X" in u:
        return '"macOS"', False
    if "Linux" in u or "X11" in u:
        return '"Linux"', False
    return '"Windows"', False


def _accept_encoding(chromium_major: Optional[int]) -> str:
    if chromium_major is not None and chromium_major >= _ZSTD_SINCE:
        return "gzip, deflate, br, zstd"
    return "gzip, deflate, br"


def _chromium(brands: str, ua: str, chromium_major: Optional[int]) -> List[Tuple[str, str]]:
    platform, mobile = _platform(ua)
    rows: List[Tuple[str, str]] = [
        ("sec-ch-ua", brands),
        ("sec-ch-ua-mobile", "?1" if mobile else "?0"),
        ("sec-ch-ua-platform", platform),
        ("upgrade-insecure-requests", "1"),
    ]
    # Chrome/Edge/Opera emit User-Agent right after upgrade-insecure-requests.
    if ua:
        rows.append(("user-agent", ua))
    rows += [
        ("accept",
         "text/html,application/xhtml+xml,application/xml;q=0.9,"
         "image/avif,image/webp,image/apng,*/*;q=0.8,"
         "application/signed-exchange;v=b3;q=0.7"),
        ("sec-fetch-site", "none"),
        ("sec-fetch-mode", "navigate"),
        ("sec-fetch-user", "?1"),
        ("sec-fetch-dest", "document"),
        ("accept-encoding", _accept_encoding(chromium_major)),
        ("accept-language", "en-US,en;q=0.9"),
        ("priority", "u=0, i"),
    ]
    return rows


def _chrome(ua: str) -> List[Tuple[str, str]]:
    m = _major(ua, "Chrome") or 131
    brands = f'"Chromium";v="{m}", {_NOT_A_BRAND}, "Google Chrome";v="{m}"'
    return _chromium(brands, ua, m)


def _edge(ua: str) -> List[Tuple[str, str]]:
    m = _major(ua, "Edg") or _major(ua, "Chrome") or 131
    brands = f'"Microsoft Edge";v="{m}", "Chromium";v="{m}", {_NOT_A_BRAND}'
    return _chromium(brands, ua, _major(ua, "Chrome") or m)


def _opera(ua: str) -> List[Tuple[str, str]]:
    chrome = _major(ua, "Chrome") or 131
    opr = _major(ua, "OPR") or 115
    brands = f'"Chromium";v="{chrome}", "Opera";v="{opr}", {_NOT_A_BRAND}'
    return _chromium(brands, ua, chrome)


def _firefox(ua: str) -> List[Tuple[str, str]]:
    # Firefox does not implement Client Hints (no sec-ch-ua) and leads with UA.
    rows: List[Tuple[str, str]] = []
    if ua:
        rows.append(("user-agent", ua))
    rows += [
        ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("accept-language", "en-US,en;q=0.5"),
        ("accept-encoding", "gzip, deflate, br, zstd"),
        ("upgrade-insecure-requests", "1"),
        ("sec-fetch-dest", "document"),
        ("sec-fetch-mode", "navigate"),
        ("sec-fetch-site", "none"),
        ("sec-fetch-user", "?1"),
        ("priority", "u=0, i"),
        ("te", "trailers"),
    ]
    return rows


def _safari(ua: str) -> List[Tuple[str, str]]:
    # Safari/iOS sends no client hints, leads with UA, and uses a leaner set.
    rows: List[Tuple[str, str]] = []
    if ua:
        rows.append(("user-agent", ua))
    rows += [
        ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("accept-language", "en-US,en;q=0.9"),
        ("accept-encoding", "gzip, deflate, br"),
    ]
    return rows


_BUILDERS = {
    "chrome": _chrome,
    "edge": _edge,
    "opera": _opera,
    "firefox": _firefox,
    "safari": _safari,
    "ios": _safari,
}


def default_browser_headers(browser: Optional[str], user_agent: Optional[str]) -> List[Tuple[str, str]]:
    """Ordered default request headers a real ``browser`` sends, or ``[]``.

    Returns an empty list for unknown/missing families so callers can merge
    unconditionally.
    """
    builder = _BUILDERS.get((browser or "").lower())
    return builder(user_agent or "") if builder else []
