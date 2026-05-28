"""Sequential POST + JSON body benchmark.

Same shape as bench_sequential.py but each request POSTs a small JSON payload.
Exercises body serialization and Content-Type handling on the request path.

Usage:
    python benchmarks/bench_post_json.py -n 500
"""
from __future__ import annotations

import asyncio
import time

from _common import (
    DEFAULT_POST_URL, parse_args, print_header, print_results, progress_done,
    progress_skip, progress_start, report_skipped, should_run,
)

PAYLOAD = {"name": "httpz-bench", "n": 42, "tags": ["bench", "post", "json"]}


def time_sync_seq(name, client, post_call, url, count, warmup):
    progress_start(name)
    for _ in range(warmup):
        try:
            post_call(client, url)
        except Exception:
            pass
    times, errors = [], 0
    t0 = time.perf_counter()
    for _ in range(count):
        t1 = time.perf_counter()
        try:
            post_call(client, url)
        except Exception:
            errors += 1
        times.append(time.perf_counter() - t1)
    total = time.perf_counter() - t0
    progress_done(name, total, errors)
    return {"name": name, "total": total, "times": times, "errors": errors}


async def time_async_seq(name, client, post_call, url, count, warmup):
    progress_start(name)
    for _ in range(warmup):
        try:
            await post_call(client, url)
        except Exception:
            pass
    times, errors = [], 0
    t0 = time.perf_counter()
    for _ in range(count):
        t1 = time.perf_counter()
        try:
            await post_call(client, url)
        except Exception:
            errors += 1
        times.append(time.perf_counter() - t1)
    total = time.perf_counter() - t0
    progress_done(name, total, errors)
    return {"name": name, "total": total, "times": times, "errors": errors}


def run_sync(url, count, warmup, only, skip, timeout=15.0):
    results, skipped = [], []
    t = timeout

    if should_run("httpz", only, skip):
        try:
            import httpz
            with httpz.Client(timeout=t) as c:
                results.append(time_sync_seq(
                    "httpz", c, lambda c, u: c.post(u, json=PAYLOAD).status_code,
                    url, count, warmup))
        except Exception as e:
            skipped.append(("httpz", str(e))); progress_skip("httpz", str(e))

    if should_run("httpx", only, skip):
        try:
            import httpx
            with httpx.Client(timeout=t) as c:
                results.append(time_sync_seq(
                    "httpx", c, lambda c, u: c.post(u, json=PAYLOAD).status_code,
                    url, count, warmup))
        except Exception as e:
            skipped.append(("httpx", str(e))); progress_skip("httpx", str(e))

    if should_run("requests", only, skip):
        try:
            import requests
            with requests.Session() as c:
                results.append(time_sync_seq(
                    "requests", c, lambda c, u: c.post(u, json=PAYLOAD, timeout=t).status_code,
                    url, count, warmup))
        except Exception as e:
            skipped.append(("requests", str(e))); progress_skip("requests", str(e))

    if should_run("curl_cffi", only, skip):
        try:
            from curl_cffi import requests as cffi_req
            with cffi_req.Session(timeout=t) as c:
                results.append(time_sync_seq(
                    "curl_cffi", c, lambda c, u: c.post(u, json=PAYLOAD).status_code,
                    url, count, warmup))
        except Exception as e:
            skipped.append(("curl_cffi", str(e))); progress_skip("curl_cffi", str(e))

    if should_run("primp", only, skip):
        try:
            import primp
            try:
                c = primp.Client(timeout=t)
            except TypeError:
                c = primp.Client()
            results.append(time_sync_seq(
                "primp", c, lambda c, u: c.post(u, json=PAYLOAD).status_code,
                url, count, warmup))
        except Exception as e:
            skipped.append(("primp", str(e))); progress_skip("primp", str(e))

    return results, skipped


async def run_async(url, count, warmup, only, skip, timeout=15.0):
    results, skipped = [], []
    t = timeout

    if should_run("httpz_async", only, skip):
        try:
            import httpz
            async with httpz.AsyncClient(timeout=t) as c:
                async def call(c, u): return (await c.post(u, json=PAYLOAD)).status_code
                results.append(await time_async_seq(
                    "httpz_async", c, call, url, count, warmup))
        except Exception as e:
            skipped.append(("httpz_async", str(e))); progress_skip("httpz_async", str(e))

    if should_run("httpx_async", only, skip):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=t) as c:
                async def call(c, u): return (await c.post(u, json=PAYLOAD)).status_code
                results.append(await time_async_seq(
                    "httpx_async", c, call, url, count, warmup))
        except Exception as e:
            skipped.append(("httpx_async", str(e))); progress_skip("httpx_async", str(e))

    if should_run("aiohttp", only, skip):
        try:
            import aiohttp
            client_timeout = aiohttp.ClientTimeout(total=t)
            async with aiohttp.ClientSession(timeout=client_timeout) as c:
                async def call(c, u):
                    async with c.post(u, json=PAYLOAD) as r:
                        await r.read()
                        return r.status
                results.append(await time_async_seq(
                    "aiohttp", c, call, url, count, warmup))
        except Exception as e:
            skipped.append(("aiohttp", str(e))); progress_skip("aiohttp", str(e))

    if should_run("curl_cffi_async", only, skip):
        try:
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(timeout=t) as c:
                async def call(c, u): return (await c.post(u, json=PAYLOAD)).status_code
                results.append(await time_async_seq(
                    "curl_cffi_async", c, call, url, count, warmup))
        except Exception as e:
            skipped.append(("curl_cffi_async", str(e))); progress_skip("curl_cffi_async", str(e))

    return results, skipped


def main():
    args = parse_args("Sequential POST+JSON benchmark")
    url = args.url or DEFAULT_POST_URL

    print_header("SEQUENTIAL POST + JSON", args.count, url)
    sync_results, sync_skipped = run_sync(
        url, args.count, args.warmup, args.only, args.skip, args.timeout)
    async_results, async_skipped = asyncio.run(run_async(
        url, args.count, args.warmup, args.only, args.skip, args.timeout))

    print()
    print_results(sync_results + async_results)
    report_skipped(sync_skipped + async_skipped)


if __name__ == "__main__":
    main()
