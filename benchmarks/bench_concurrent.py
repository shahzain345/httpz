"""Concurrent GET benchmark: N parallel GETs against one shared client.

Sync libraries use a ThreadPoolExecutor with `concurrency` workers; async
libraries use asyncio.gather bounded by a Semaphore of size `concurrency`.

This measures throughput under load — pool reuse, contention, scheduling
overhead. Be modest with -n against public endpoints (httpbin rate-limits).

Usage:
    python benchmarks/bench_concurrent.py -n 500 -c 20
"""
from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from _common import (
    DEFAULT_GET_URL, parse_args, print_header, print_results, progress_done,
    progress_skip, progress_start, report_skipped, should_run,
)


def time_sync_concurrent(name, client, get_call, url, count, concurrency, warmup):
    progress_start(name)
    for _ in range(warmup):
        try:
            get_call(client, url)
        except Exception:
            pass

    times = [0.0] * count
    errors = [0]

    def worker(i):
        t1 = time.perf_counter()
        try:
            get_call(client, url)
        except Exception:
            errors[0] += 1
        times[i] = time.perf_counter() - t1

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(worker, range(count)))
    total = time.perf_counter() - t0
    progress_done(name, total, errors[0])
    return {"name": name, "total": total, "times": times, "errors": errors[0]}


async def time_async_concurrent(name, client, get_call, url, count, concurrency, warmup):
    progress_start(name)
    for _ in range(warmup):
        try:
            await get_call(client, url)
        except Exception:
            pass

    sem = asyncio.Semaphore(concurrency)
    times = [0.0] * count
    errors = [0]

    async def task(i):
        async with sem:
            t1 = time.perf_counter()
            try:
                await get_call(client, url)
            except Exception:
                errors[0] += 1
            times[i] = time.perf_counter() - t1

    t0 = time.perf_counter()
    await asyncio.gather(*(task(i) for i in range(count)))
    total = time.perf_counter() - t0
    progress_done(name, total, errors[0])
    return {"name": name, "total": total, "times": times, "errors": errors[0]}


def run_sync(url, count, concurrency, warmup, only, skip, timeout=15.0):
    results, skipped = [], []
    t = timeout

    if should_run("httpz", only, skip):
        try:
            import httpz
            with httpz.Client(timeout=t) as c:
                results.append(time_sync_concurrent(
                    "httpz", c, lambda c, u: c.get(u).status_code,
                    url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("httpz", str(e))); progress_skip("httpz", str(e))

    if should_run("httpx", only, skip):
        try:
            import httpx
            with httpx.Client(timeout=t) as c:
                results.append(time_sync_concurrent(
                    "httpx", c, lambda c, u: c.get(u).status_code,
                    url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("httpx", str(e))); progress_skip("httpx", str(e))

    if should_run("requests", only, skip):
        try:
            import requests
            with requests.Session() as c:
                results.append(time_sync_concurrent(
                    "requests", c, lambda c, u: c.get(u, timeout=t).status_code,
                    url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("requests", str(e))); progress_skip("requests", str(e))

    if should_run("curl_cffi", only, skip):
        try:
            from curl_cffi import requests as cffi_req
            with cffi_req.Session(timeout=t) as c:
                results.append(time_sync_concurrent(
                    "curl_cffi", c, lambda c, u: c.get(u).status_code,
                    url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("curl_cffi", str(e))); progress_skip("curl_cffi", str(e))

    if should_run("primp", only, skip):
        try:
            import primp
            try:
                c = primp.Client(timeout=t)
            except TypeError:
                c = primp.Client()
            results.append(time_sync_concurrent(
                "primp", c, lambda c, u: c.get(u).status_code,
                url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("primp", str(e))); progress_skip("primp", str(e))

    return results, skipped


async def run_async(url, count, concurrency, warmup, only, skip, timeout=15.0):
    results, skipped = [], []
    t = timeout

    if should_run("httpz_async", only, skip):
        try:
            import httpz
            async with httpz.AsyncClient(timeout=t) as c:
                async def call(c, u): return (await c.get(u)).status_code
                results.append(await time_async_concurrent(
                    "httpz_async", c, call, url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("httpz_async", str(e))); progress_skip("httpz_async", str(e))

    if should_run("httpx_async", only, skip):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=t) as c:
                async def call(c, u): return (await c.get(u)).status_code
                results.append(await time_async_concurrent(
                    "httpx_async", c, call, url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("httpx_async", str(e))); progress_skip("httpx_async", str(e))

    if should_run("aiohttp", only, skip):
        try:
            import aiohttp
            connector = aiohttp.TCPConnector(limit=concurrency)
            client_timeout = aiohttp.ClientTimeout(total=t)
            async with aiohttp.ClientSession(connector=connector, timeout=client_timeout) as c:
                async def call(c, u):
                    async with c.get(u) as r:
                        await r.read()
                        return r.status
                results.append(await time_async_concurrent(
                    "aiohttp", c, call, url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("aiohttp", str(e))); progress_skip("aiohttp", str(e))

    if should_run("curl_cffi_async", only, skip):
        try:
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(timeout=t) as c:
                async def call(c, u): return (await c.get(u)).status_code
                results.append(await time_async_concurrent(
                    "curl_cffi_async", c, call, url, count, concurrency, warmup))
        except Exception as e:
            skipped.append(("curl_cffi_async", str(e))); progress_skip("curl_cffi_async", str(e))

    return results, skipped


def main():
    args = parse_args("Concurrent GET benchmark (one shared client, N parallel GETs)")
    url = args.url or DEFAULT_GET_URL

    print_header("CONCURRENT GETs", args.count, url, concurrency=args.concurrency)
    sync_results, sync_skipped = run_sync(
        url, args.count, args.concurrency, args.warmup, args.only, args.skip, args.timeout)
    async_results, async_skipped = asyncio.run(run_async(
        url, args.count, args.concurrency, args.warmup, args.only, args.skip, args.timeout))

    print()
    print_results(sync_results + async_results)
    report_skipped(sync_skipped + async_skipped)


if __name__ == "__main__":
    main()
