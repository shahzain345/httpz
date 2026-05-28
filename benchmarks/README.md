# httpz benchmarks

Compares httpz against httpx, requests, curl_cffi, primp, and aiohttp.

## Layout

| File | Scenario |
|---|---|
| `bench_cold_start.py` | Build a client + 1 GET, repeated (measures setup cost) |
| `bench_sequential.py` | One client, N back-to-back GETs (steady-state per-request overhead) |
| `bench_concurrent.py` | One client, N parallel GETs (throughput under load) |
| `bench_post_json.py` | One client, N sequential POSTs with a JSON body |
| `run_all.py` | Runs all four in order |
| `_common.py` | Shared CLI parsing, timing, results table |

## Run

```powershell
# Everything with defaults (cold=50, others=500)
python benchmarks\run_all.py

# A single scenario
python benchmarks\bench_sequential.py -n 500

# A smaller, faster pass
python benchmarks\run_all.py -n 50 -c 5

# Leave a library out (useful if one is rate-limited)
python benchmarks\bench_concurrent.py --skip primp curl_cffi_async

# Run only specific libs
python benchmarks\bench_sequential.py --only httpz httpx aiohttp
```

## Libraries covered

Sync clients: `httpz`, `httpx`, `requests`, `curl_cffi`, `primp`
Async clients: `httpz` (AsyncClient), `httpx` (AsyncClient), `aiohttp`, `curl_cffi` (AsyncSession)

If a library is missing or fails to construct, it's listed under **Skipped** at the bottom of the table instead of crashing the run.

## Output

Each scenario prints one table sorted by total time (fastest first):

```
Library            Total (s)     req/s   mean (ms)     p50     p95     p99  errors
--------------------------------------------------------------------------------
httpz                  12.34      40.5        24.7    22.1    41.2    62.0       0
...
```

## Notes on fairness and noise

- Defaults target `httpbin.org`. It's rate-limited and noisy — expect variance, and lower `-n` if you see 429s.
- For stable numbers, point the benches at a local server: `python benchmarks\bench_sequential.py --url http://127.0.0.1:8000/`
- Each scenario does a warmup pass (default 3 requests) so TLS/DNS setup isn't billed to the first timed request.
- The concurrent bench shares one client across workers — this matches idiomatic usage but means thread/asyncio scheduling overhead is part of what's measured.
- `primp` doesn't expose a context manager; its client is constructed and used directly.
