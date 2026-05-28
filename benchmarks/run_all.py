"""Run every benchmark in sequence and print results in one go.

Defaults are intentionally modest because httpbin.org is slow and rate-limits.
Each library is timed one at a time and prints `-> name: running...` /
`-> name: 12.3s (0 errors)` so you can see live progress.

Usage:
    python benchmarks/run_all.py                # modest defaults
    python benchmarks/run_all.py -n 100 -c 10   # heavier pass
    python benchmarks/run_all.py --skip primp   # leave one library out
    python benchmarks/run_all.py --url http://127.0.0.1:8000/   # local server
"""
from __future__ import annotations

import argparse
import asyncio

import bench_cold_start
import bench_sequential
import bench_concurrent
import bench_post_json
from _common import (
    DEFAULT_GET_URL, DEFAULT_POST_URL, print_header, print_results,
    report_skipped,
)


def main():
    p = argparse.ArgumentParser(description="Run every httpz benchmark")
    p.add_argument("-n", "--count", type=int, default=None,
                   help="Override request count for all benches (default: per-bench)")
    p.add_argument("--cold-count", type=int, default=10,
                   help="Cold-start iterations (default 10)")
    p.add_argument("--seq-count", type=int, default=50,
                   help="Sequential GET requests per lib (default 50)")
    p.add_argument("--concurrent-count", type=int, default=50,
                   help="Concurrent GET requests per lib (default 50)")
    p.add_argument("--post-count", type=int, default=50,
                   help="POST+JSON requests per lib (default 50)")
    p.add_argument("-c", "--concurrency", type=int, default=10)
    p.add_argument("--warmup", type=int, default=2)
    p.add_argument("--timeout", type=float, default=15.0,
                   help="Per-request timeout in seconds (default 15.0)")
    p.add_argument("--get-url", default=DEFAULT_GET_URL)
    p.add_argument("--post-url", default=DEFAULT_POST_URL)
    p.add_argument("--only", nargs="+", default=None)
    p.add_argument("--skip", nargs="+", default=[])
    args = p.parse_args()

    cold_n = args.count or args.cold_count
    seq_n = args.count or args.seq_count
    conc_n = args.count or args.concurrent_count
    post_n = args.count or args.post_count

    # 1. Cold-start
    print_header("COLD-START (construct + 1 GET)", cold_n, args.get_url)
    sr, ss = bench_cold_start.run_sync(
        args.get_url, cold_n, args.only, args.skip, args.timeout)
    ar, ass_ = asyncio.run(bench_cold_start.run_async(
        args.get_url, cold_n, args.only, args.skip, args.timeout))
    print()
    print_results(sr + ar)
    report_skipped(ss + ass_)

    # 2. Sequential GET
    print_header("SEQUENTIAL GETs", seq_n, args.get_url)
    sr, ss = bench_sequential.run_sync(
        args.get_url, seq_n, args.warmup, args.only, args.skip, args.timeout)
    ar, ass_ = asyncio.run(bench_sequential.run_async(
        args.get_url, seq_n, args.warmup, args.only, args.skip, args.timeout))
    print()
    print_results(sr + ar)
    report_skipped(ss + ass_)

    # 3. Concurrent GET
    print_header("CONCURRENT GETs", conc_n, args.get_url, concurrency=args.concurrency)
    sr, ss = bench_concurrent.run_sync(
        args.get_url, conc_n, args.concurrency, args.warmup,
        args.only, args.skip, args.timeout)
    ar, ass_ = asyncio.run(bench_concurrent.run_async(
        args.get_url, conc_n, args.concurrency, args.warmup,
        args.only, args.skip, args.timeout))
    print()
    print_results(sr + ar)
    report_skipped(ss + ass_)

    # 4. POST + JSON
    print_header("SEQUENTIAL POST + JSON", post_n, args.post_url)
    sr, ss = bench_post_json.run_sync(
        args.post_url, post_n, args.warmup, args.only, args.skip, args.timeout)
    ar, ass_ = asyncio.run(bench_post_json.run_async(
        args.post_url, post_n, args.warmup, args.only, args.skip, args.timeout))
    print()
    print_results(sr + ar)
    report_skipped(ss + ass_)


if __name__ == "__main__":
    main()
