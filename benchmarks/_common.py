"""Shared utilities for the httpz benchmark suite.

Each bench_*.py script imports from here:
  - parse_args(): consistent CLI flags across benchmarks
  - print_results(): single results-table format
  - percentile(): no-numpy percentile so the suite has no extra deps
  - DEFAULT_GET_URL / DEFAULT_POST_URL: target endpoints

The sync benchmarks measure libraries that expose a blocking API: httpz, httpx,
requests, curl_cffi, primp. The async benchmarks measure libraries with an
asyncio API: httpz.AsyncClient, httpx.AsyncClient, aiohttp, curl_cffi async.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import os

# Make the httpz source tree importable when running scripts directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_GET_URL = "https://httpbin.org/get"
DEFAULT_POST_URL = "https://httpbin.org/post"

ALL_SYNC_LIBS = ["httpz", "httpx", "requests", "curl_cffi", "primp"]
ALL_ASYNC_LIBS = ["httpz_async", "httpx_async", "aiohttp", "curl_cffi_async"]


def parse_args(description: str, default_count: int = 500, default_concurrency: int = 20):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("-n", "--count", type=int, default=default_count,
                   help=f"Number of requests per library (default {default_count})")
    p.add_argument("-c", "--concurrency", type=int, default=default_concurrency,
                   help=f"Parallel workers for concurrent benches (default {default_concurrency})")
    p.add_argument("--url", default=None, help="Override target URL")
    p.add_argument("--warmup", type=int, default=3,
                   help="Warmup requests per library before timing (default 3)")
    p.add_argument("--timeout", type=float, default=15.0,
                   help="Per-request timeout in seconds (default 15.0)")
    p.add_argument("--only", nargs="+", default=None,
                   help="Run only these libs (space-separated)")
    p.add_argument("--skip", nargs="+", default=[],
                   help="Skip these libs (space-separated)")
    return p.parse_args()


def progress_start(name: str):
    print(f"  -> {name}: running...", flush=True)


def progress_done(name: str, total: float, errors: int):
    print(f"  -> {name}: {total:.1f}s ({errors} errors)", flush=True)


def progress_skip(name: str, reason: str):
    short = reason.splitlines()[0][:120]
    print(f"  -> {name}: SKIPPED ({short})", flush=True)


def percentile(data, p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def should_run(name: str, only, skip) -> bool:
    if only and name not in only:
        return False
    if name in skip:
        return False
    return True


def print_header(title: str, count: int, url: str, concurrency: int | None = None):
    print()
    print("=" * 100)
    line = f"  {title}   n={count}   url={url}"
    if concurrency is not None:
        line += f"   concurrency={concurrency}"
    print(line)
    print("=" * 100)


def print_results(results):
    """results: list of dicts with name, total, times (list of seconds), errors."""
    print(f"{'Library':<18} {'Total (s)':>10} {'req/s':>9} {'mean (ms)':>11} "
          f"{'p50':>7} {'p95':>7} {'p99':>7} {'errors':>7}")
    print("-" * 80)
    rows = sorted(results, key=lambda r: r["total"])
    for r in rows:
        ts = r["times"]
        if ts:
            mean_ms = statistics.mean(ts) * 1000
            p50 = percentile(ts, 50) * 1000
            p95 = percentile(ts, 95) * 1000
            p99 = percentile(ts, 99) * 1000
        else:
            mean_ms = p50 = p95 = p99 = 0.0
        good = len(ts) - r["errors"] if r["errors"] <= len(ts) else 0
        rps = good / r["total"] if r["total"] > 0 else 0.0
        print(f"{r['name']:<18} {r['total']:>10.2f} {rps:>9.1f} {mean_ms:>11.1f} "
              f"{p50:>7.1f} {p95:>7.1f} {p99:>7.1f} {r['errors']:>7}")
    print()


def report_skipped(skipped: list[tuple[str, str]]):
    if not skipped:
        return
    print("Skipped:")
    for name, reason in skipped:
        print(f"  - {name}: {reason}")
    print()
