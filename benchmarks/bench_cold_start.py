"""Cold-start benchmark: client construction + 1 GET, repeated N times.

Each iteration creates a brand new client. This measures setup cost (TLS
handshake, internal pool init, FFI bridge handshake for httpz, etc.) which is
the cost short-lived scripts and CLI tools pay.

Usage:
    python benchmarks/bench_cold_start.py -n 50
"""
from __future__ import annotations

import asyncio
import time

from _common import (
    DEFAULT_GET_URL, parse_args, print_header, print_results, progress_done,
    progress_skip, progress_start, report_skipped, should_run,
)


def time_sync_cold(name, ctor, get_call, url, count):
    progress_start(name)
    times, errors = [], 0
    t0 = time.perf_counter()
    for _ in range(count):
        t1 = time.perf_counter()
        try:
            client = ctor()
            try:
                get_call(client, url)
            finally:
                _close_quietly(client)
        except Exception:
            errors += 1
        times.append(time.perf_counter() - t1)
    total = time.perf_counter() - t0
    progress_done(name, total, errors)
    return {"name": name, "total": total, "times": times, "errors": errors}


async def time_async_cold(name, ctor, get_call, url, count):
    progress_start(name)
    times, errors = [], 0
    t0 = time.perf_counter()
    for _ in range(count):
        t1 = time.perf_counter()
        try:
            client = ctor()
            try:
                await get_call(client, url)
            finally:
                await _aclose_quietly(client)
        except Exception:
            errors += 1
        times.append(time.perf_counter() - t1)
    total = time.perf_counter() - t0
    progress_done(name, total, errors)
    return {"name": name, "total": total, "times": times, "errors": errors}


def _close_quietly(client):
    for attr in ("close", "__exit__"):
        fn = getattr(client, attr, None)
        if fn is None:
            continue
        try:
            if attr == "__exit__":
                fn(None, None, None)
            else:
                fn()
            return
        except Exception:
            pass


async def _aclose_quietly(client):
    aclose = getattr(client, "aclose", None) or getattr(client, "close", None)
    if aclose is None:
        return
    try:
        result = aclose()
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        pass


def run_sync(url, count, only, skip, timeout=15.0):
    results, skipped = [], []
    t = timeout

    if should_run("httpz", only, skip):
        try:
            import httpz
            results.append(time_sync_cold(
                "httpz", lambda: httpz.Client(timeout=t),
                lambda c, u: c.get(u).status_code, url, count))
        except Exception as e:
            skipped.append(("httpz", str(e))); progress_skip("httpz", str(e))

    if should_run("httpx", only, skip):
        try:
            import httpx
            results.append(time_sync_cold(
                "httpx", lambda: httpx.Client(timeout=t),
                lambda c, u: c.get(u).status_code, url, count))
        except Exception as e:
            skipped.append(("httpx", str(e))); progress_skip("httpx", str(e))

    if should_run("requests", only, skip):
        try:
            import requests
            results.append(time_sync_cold(
                "requests", lambda: requests.Session(),
                lambda c, u: c.get(u, timeout=t).status_code, url, count))
        except Exception as e:
            skipped.append(("requests", str(e))); progress_skip("requests", str(e))

    if should_run("curl_cffi", only, skip):
        try:
            from curl_cffi import requests as cffi_req
            results.append(time_sync_cold(
                "curl_cffi", lambda: cffi_req.Session(timeout=t),
                lambda c, u: c.get(u).status_code, url, count))
        except Exception as e:
            skipped.append(("curl_cffi", str(e))); progress_skip("curl_cffi", str(e))

    if should_run("primp", only, skip):
        try:
            import primp
            def make():
                try:
                    return primp.Client(timeout=t)
                except TypeError:
                    return primp.Client()
            results.append(time_sync_cold(
                "primp", make,
                lambda c, u: c.get(u).status_code, url, count))
        except Exception as e:
            skipped.append(("primp", str(e))); progress_skip("primp", str(e))

    return results, skipped


async def run_async(url, count, only, skip, timeout=15.0):
    results, skipped = [], []
    t = timeout

    if should_run("httpz_async", only, skip):
        try:
            import httpz
            async def call(c, u): return (await c.get(u)).status_code
            results.append(await time_async_cold(
                "httpz_async", lambda: httpz.AsyncClient(timeout=t), call, url, count))
        except Exception as e:
            skipped.append(("httpz_async", str(e))); progress_skip("httpz_async", str(e))

    if should_run("httpx_async", only, skip):
        try:
            import httpx
            async def call(c, u): return (await c.get(u)).status_code
            results.append(await time_async_cold(
                "httpx_async", lambda: httpx.AsyncClient(timeout=t), call, url, count))
        except Exception as e:
            skipped.append(("httpx_async", str(e))); progress_skip("httpx_async", str(e))

    if should_run("aiohttp", only, skip):
        try:
            import aiohttp
            client_timeout = aiohttp.ClientTimeout(total=t)
            async def call(c, u):
                async with c.get(u) as r:
                    await r.read()
                    return r.status
            results.append(await time_async_cold(
                "aiohttp", lambda: aiohttp.ClientSession(timeout=client_timeout),
                call, url, count))
        except Exception as e:
            skipped.append(("aiohttp", str(e))); progress_skip("aiohttp", str(e))

    if should_run("curl_cffi_async", only, skip):
        try:
            from curl_cffi.requests import AsyncSession
            async def call(c, u): return (await c.get(u)).status_code
            results.append(await time_async_cold(
                "curl_cffi_async", lambda: AsyncSession(timeout=t), call, url, count))
        except Exception as e:
            skipped.append(("curl_cffi_async", str(e))); progress_skip("curl_cffi_async", str(e))

    return results, skipped


def main():
    args = parse_args("Cold-start benchmark (client construction + 1 GET)",
                      default_count=50)
    url = args.url or DEFAULT_GET_URL

    print_header("COLD-START (construct + 1 GET, repeated)", args.count, url)
    sync_results, sync_skipped = run_sync(
        url, args.count, args.only, args.skip, args.timeout)
    async_results, async_skipped = asyncio.run(run_async(
        url, args.count, args.only, args.skip, args.timeout))

    print()
    print_results(sync_results + async_results)
    report_skipped(sync_skipped + async_skipped)


if __name__ == "__main__":
    main()
