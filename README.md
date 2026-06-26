<p align="center">
  <img src="https://gay-fags.discowd.com/r/httpz.png" alt="httpz logo" width="200">
</p>

<h1 align="center">httpz</h1>

<p align="center">
  <b>An HTTP client for Python with first-class TLS fingerprint control.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/pyhttpz/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pyhttpz?color=4c1&label=pypi"></a>
  <img alt="Python versions" src="https://img.shields.io/pypi/pyversions/pyhttpz?color=blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <a href="https://discord.gg/4793Cm3kc2"><img alt="Discord" src="https://img.shields.io/badge/discord-join%20the%20community-5865F2?logo=discord&logoColor=white"></a>
</p>

<p align="center">
  <a href="https://github.com/shahzain345/shahzain345.github.io/blob/main/README.md"><b>📖 Documentation</b></a>
  &nbsp;·&nbsp;
  <a href="#quick-examples">Examples</a>
  &nbsp;·&nbsp;
  <a href="#impersonate-presets">Presets</a>
  &nbsp;·&nbsp;
  <a href="#benchmarks">Benchmarks</a>
  &nbsp;·&nbsp;
  <a href="https://discord.gg/4793Cm3kc2">Discord</a>
</p>

---

Most Python HTTP clients let you set headers. httpz lets you set the **TLS handshake itself** — hand it a JA3 string and the ClientHello on the wire is rewritten to match it, byte for byte. Same goes for the **HTTP/2 (Akamai)** fingerprint. And since the API is shaped like `httpx`, porting existing code is usually just a change of import.

The short version: pass `impersonate="chrome131"` and your request looks like Chrome — its TLS fingerprint, its HTTP/2 fingerprint, its User-Agent, *and* the exact headers it sends, in the order it sends them. Not just a spoofed User-Agent string.

Under the hood it wraps [azuretls-client](https://github.com/Noooste/azuretls-client) (Go) as a shared library, so there's a real, battle-tested TLS engine behind the Pythonic surface.

```python
import httpz

with httpz.Client(
    ja3="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
    browser="chrome",
) as client:
    r = client.get("https://tls.peet.ws/api/all")
    print(r.json())   # the JA3 you set is the JA3 the server sees
```

---

## Why httpz

The existing options — `curl_cffi`, `tls_client`, patched `pycurl` — mostly hand you a fixed menu of browser presets, or some low-level knob arrangement that breaks the next time you upgrade. httpz takes the other approach: give it *any* JA3 string and it just works. No preset enum to wait on, no rebuild step, no urllib3 fork to maintain — `ja3="..."` on the constructor and you're done.

And it's still a normal HTTP client underneath. Sync and async, sessions with cookie jars, proxies (http / https / socks5), HTTP/2, and an `httpx`-shaped request/response API. You don't give up the everyday conveniences to get the fingerprinting.

---

## Features

### TLS fingerprint control

- **Custom JA3** — supply any JA3 fingerprint string and httpz reproduces the exact ClientHello (cipher suites, extensions, elliptic curves, point formats) at the TLS layer.
- **Custom HTTP/2 (Akamai) fingerprint** — set SETTINGS, WINDOW_UPDATE, header pseudo-header ordering, and priority frames via a single Akamai-format string.
- **Browser presets** — `chrome`, `firefox`, `safari`, `edge`, `opera`, `ios` for one-line spoofing without writing a JA3 by hand.
- **`impersonate="..."` — 170 pre-canned browser presets** covering Chrome, Firefox, Safari, Edge and Opera (see [Impersonate presets](#impersonate-presets) below). Each preset also sends that browser's real **default request headers** (client hints, `Accept`, `Sec-Fetch-*`, …), so the request matches a browser at the HTTP layer too — not just the TLS/HTTP2 handshake.
- **Apply at runtime** — `client.apply_ja3(...)` and `client.apply_h2_fingerprint(...)` reconfigure a live session without rebuilding it.

```python
client = httpz.Client(browser=httpz.CHROME)
client.apply_ja3("771,4865-...", browser="chrome")
client.apply_h2_fingerprint("1:65536;2:0;4:6291456;6:262144|15663105|0|m,s,a,p")
```

### Impersonate presets

`impersonate="chrome131"` is a one-shot shorthand that sets JA3 + Akamai (H2) fingerprint + User-Agent + browser navigator all at once:

```python
with httpz.Client(impersonate="chrome131") as c:
    r = c.get("https://tls.peet.ws/api/all")
    print(r.json()["tls"]["ja3_hash"])  # matches the chrome131 profile exactly

# Some versions ship more than one distinct on-the-wire profile (e.g. a
# different TLS extension order). They live under sibling names like
# `chrome131`, `chrome_131` and `chrome131a` — each a real, distinct handshake.
with httpz.Client(impersonate="chrome_131") as c:
    ...

# Any explicit kwarg overrides the preset
with httpz.Client(impersonate="chrome131", user_agent="MyBot/1.0") as c:
    ...
```

**170 unique browser profiles** (219 names total once aliases are counted — names like `safari17_0` and `safari_17.0` resolve to the same canonical profile because the bytes-on-the-wire are identical).

#### Browser default headers

A real Chrome request isn't just a TLS handshake — it also carries a recognizable set of HTTP headers (`sec-ch-ua`, `Accept`, `Sec-Fetch-*`, `Accept-Language`, `priority`, …). A request with a perfect JA3 but none of those headers is still easy to flag as non-browser.

So whenever a browser navigator is active (`impersonate=` or `browser=`), httpz automatically sends that browser's default headers, with values derived from the preset (e.g. the `sec-ch-ua` version and `Accept-Encoding` track the Chrome version; the platform/mobile hints track the User-Agent):

```python
with httpz.Client(impersonate="chrome146") as c:
    c.get("https://tls.peet.ws/api/all")
# sends sec-ch-ua / sec-ch-ua-mobile / sec-ch-ua-platform /
# upgrade-insecure-requests / accept / sec-fetch-* /
# accept-encoding / accept-language / priority — like real Chrome
```

The headers (including `User-Agent`) are emitted in each browser's natural order — e.g. Chrome/Edge/Opera place `user-agent` right after `upgrade-insecure-requests`, while Firefox and Safari lead with it — so the on-the-wire header order matches a real browser, not just the header set.

Anything you pass in `headers=` overrides a default per key (keeping the browser's header order); extra headers are appended. To send only the headers you specify, pass `browser_headers=False`:

```python
# Override one default, add one of your own — the rest of Chrome's headers stay
httpz.Client(impersonate="chrome146", headers={"accept-language": "fr-FR,fr;q=0.9"})

# Opt out entirely
httpz.Client(impersonate="chrome146", browser_headers=False)
```

Firefox and Safari presets send their own (client-hint-free) header sets accordingly.

#### Every profile you can impersonate

<details>
<summary><b>All 170 profiles, grouped by browser</b> — click to expand</summary>

<br>

##### Chrome (78)
`chrome99`, `chrome99_android`, `chrome100`, `chrome101`, `chrome104`, `chrome106a`, `chrome107`, `chrome107a`, `chrome108a`, `chrome109a`, `chrome110`, `chrome110a`, `chrome114a`, `chrome116`, `chrome116a`, `chrome117a`, `chrome118a`, `chrome119`, `chrome119a`, `chrome120`, `chrome120a`, `chrome123`, `chrome123a`, `chrome124`, `chrome124a`, `chrome126a`, `chrome127a`, `chrome128a`, `chrome129a`, `chrome130a`, `chrome131`, `chrome131_android`, `chrome131a`, `chrome132`, `chrome133a`, `chrome133b`, `chrome134`, `chrome135`, `chrome136`, `chrome136a`, `chrome137`, `chrome138`, `chrome139`, `chrome140`, `chrome141`, `chrome142`, `chrome142a`, `chrome143`, `chrome144`, `chrome145`, `chrome145a`, `chrome146`, `chrome146a`, `chrome147`, `chrome148`, `chrome_100`, `chrome_101`, `chrome_104`, `chrome_105`, `chrome_106`, `chrome_107`, `chrome_108`, `chrome_109`, `chrome_114`, `chrome_116`, `chrome_117`, `chrome_118`, `chrome_119`, `chrome_120`, `chrome_123`, `chrome_124`, `chrome_126`, `chrome_127`, `chrome_128`, `chrome_129`, `chrome_130`, `chrome_131`, `chrome_133`

##### Firefox (20)
`firefox133`, `firefox135`, `firefox136`, `firefox139`, `firefox142`, `firefox143`, `firefox144`, `firefox145`, `firefox146`, `firefox147`, `firefox148`, `firefox149`, `firefox151`, `firefox_109`, `firefox_117`, `firefox_128`, `firefoxandroid135`, `firefoxprivate135`, `firefoxprivate136`, `tor145`

##### Safari (34)
`safari26`, `safari153`, `safari155`, `safari170`, `safari172_ios`, `safari180`, `safari180_ios`, `safari183`, `safari184`, `safari184_ios`, `safari185`, `safari260`, `safari260_ios`, `safari261`, `safari262`, `safari1831`, `safari2601`, `safari_15.3`, `safari_15.5`, `safari_15.6.1`, `safari_16`, `safari_16.5`, `safari_17.2.1`, `safari_17.4.1`, `safari_17.5`, `safari_18.2`, `safari_ios_16.5`, `safari_ios_17.4.1`, `safari_ios_18.1.1`, `safari_ipad_18`, `safariios26`, `safariios262`, `safariipad26`, `safariipad262`

##### Edge (23)
`edge99`, `edge101`, `edge122a`, `edge127a`, `edge131a`, `edge134`, `edge135`, `edge136`, `edge137`, `edge138`, `edge139`, `edge140`, `edge141`, `edge142`, `edge143`, `edge144`, `edge145`, `edge146`, `edge147`, `edge_101`, `edge_122`, `edge_127`, `edge_131`

##### Opera (15)
`opera116`, `opera117`, `opera118`, `opera119`, `opera120`, `opera121`, `opera122`, `opera123`, `opera124`, `opera125`, `opera126`, `opera127`, `opera128`, `opera129`, `opera130`

</details>

#### How name lookup works

Names are normalized before lookup, so all of these resolve to the same profile: `chrome131`, `chrome_131`, `Chrome131`, `CHROME131` (after normalization that strips underscores/dots and lowercases). When a browser version has more than one distinct handshake on the wire, each variant keeps its own name (a sibling suffix like `_131` or `131a`) so every unique profile stays reachable.

List everything at runtime:

```python
import httpz
print(httpz.list_impersonate_targets())          # every resolvable name
print(httpz.resolve_impersonate("chrome131"))    # full preset dict
```

#### Refreshing the presets

The presets are embedded directly in `httpz/presets.py` (as a Python dict, so compiled/bundled builds pick them up automatically — no separate data file to include) and are generated by `scripts/scrape_fingerprints.py`.

```bash
# Full rebuild from all sources (drops manual entries):
pip install -U curl_cffi primp wreq
python scripts/scrape_fingerprints.py

# Or add ONLY new profiles from one source on top of the current presets,
# skipping any whose fingerprint already exists (keeps manual entries):
python scripts/scrape_fingerprints.py --augment --only wreq
```

The scraper enumerates every impersonate target each library exposes, makes a real request through that library to `https://tls.peet.ws/api/all`, captures the JA3 + Akamai fingerprint + User-Agent the server saw, dedupes any names that produce byte-identical handshakes, and regenerates `httpz/presets.py` with the result embedded as a Python dict. In `--augment` mode a freshly scraped profile is added only when its `(ja3, h2_fingerprint, user_agent)` isn't already present; duplicates are skipped so nothing is stored twice. Manually-added profiles (the `source: "manual"` entries) are preserved by `--augment` but dropped by a full rebuild — keep a backup if you've curated any.

#### A note on TLS extension 41 (pre_shared_key)

If you paste in a JA3 captured from a live browser session that includes extension `41` at the end of the extension list, strip it before saving the preset. TLS 1.3 `pre_shared_key` is only valid in a ClientHello when accompanied by real session-resumption material — without it the server rejects the handshake. `curl_cffi`/`utls`/`azuretls` all drop it on the way out, so the resulting JA3 on the wire never contains 41. The dedupe step in `scripts/scrape_fingerprints.py` doesn't strip extensions — you'd do that by hand when adding a manual preset.

### Sync and async clients

- `httpz.Client` — blocking, `with`-context safe, modeled after `httpx.Client`.
- `httpz.AsyncClient` — `async with`-context safe, mirrors `httpx.AsyncClient`. Runs the FFI bridge calls in a thread pool so it never blocks the event loop.

```python
# Sync
with httpz.Client() as c:
    r = c.get("https://example.com")

# Async
async with httpz.AsyncClient() as c:
    r = await c.get("https://example.com")
```

### Module-level shortcuts

`httpz.get`, `httpz.post`, `httpz.put`, `httpz.patch`, `httpz.delete`, `httpz.head`, `httpz.options` — for one-off calls that build, use, and dispose of a client in one line.

### Request features

- **HTTP methods**: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS.
- **JSON bodies**: `client.post(url, json={...})` — automatic serialization and `Content-Type`.
- **Form bodies**: `client.post(url, data={...})` — URL-encoded with the right `Content-Type`.
- **Raw bytes**: `client.post(url, content=b"...")` for arbitrary payloads.
- **Query params**: `client.get(url, params={"q": "x"})` — merged with any existing query string.
- **Headers**: defaults set on the client, plus per-request overrides; case-insensitive multi-dict.
- **Cookies**: a `Cookies` jar that auto-syncs with `Set-Cookie` responses and re-sends on subsequent requests.
- **Redirects**: `follow_redirects` and `max_redirects` per request.
- **Timeouts**: client-default or per-request (`timeout=...` in seconds).
- **TLS verify** toggle: `verify=False` for self-signed certs in dev.

### Sessions, proxies, and networking

- **Proxy support**: `proxy="http://..."`, `"https://..."`, or `"socks5://..."`. Settable at construction or via `set_proxy(...)` / `clear_proxy()`.
- **Cookie persistence** within the session (managed by the Go-side jar).
- **HTTP/2** by default when the server negotiates it.
- **Force HTTP/1.1**: `force_http1=True` disables HTTP/2 negotiation — settable at the client level or per request.
- **User-Agent** override at the client level.

### Forcing HTTP/1.1

By default httpz uses HTTP/2 whenever the server negotiates it. Pass
`force_http1=True` to disable HTTP/2 and pin the connection to HTTP/1.1. It works
at both the client level (applies to every request) and per request, and a
per-request value overrides the client default:

```python
# Client-level: every request through this client is HTTP/1.1
with httpz.Client(impersonate="chrome131", force_http1=True) as c:
    r = c.get("https://tls.peet.ws/api/clean")
    print(r.http_version)   # HTTP/1.1

# Per request: force just this one call over HTTP/1.1
with httpz.Client(impersonate="chrome131") as c:
    r = c.get("https://example.com", force_http1=True)
    print(r.http_version)   # HTTP/1.1

# Per-request override: opt one call back into HTTP/2 on a forced client
with httpz.Client(impersonate="chrome131", force_http1=True) as c:
    r = c.get("https://example.com", force_http1=False)
    print(r.http_version)   # HTTP/2.0
```

The same `force_http1=` argument works on `httpz.AsyncClient` and on the
module-level shortcuts (`httpz.get(...)`, `httpz.post(...)`, …).

### Response API

A response object modeled after `httpx.Response`:

- `r.status_code`, `r.ok`, `r.is_success`
- `r.text`, `r.content` (bytes), `r.json()`
- `r.headers` (Headers multi-dict), `r.cookies` (Cookies)
- `r.url`, `r.http_version`
- `r.raise_for_status()`

### Exceptions

A small, structured exception tree rooted at `HTTPZError`:

`TransportError`, `BridgeError`, `TimeoutError`, `ProxyError`, `TooManyRedirects`, `ConnectionError`, `HTTPStatusError`.

---

## Quick examples

```python
# 1. Browser-emulated GET (using a pre-canned impersonate preset)
with httpz.Client(impersonate="chrome131") as c:
    r = c.get("https://tls.peet.ws/api/all")
    print(r.json()["tls"]["ja3_hash"])

# 2. POST JSON through a SOCKS5 proxy
with httpz.Client(proxy="socks5://user:pass@127.0.0.1:1080") as c:
    r = c.post("https://api.example.com/v1/items", json={"name": "x"})
    r.raise_for_status()

# 3. Custom JA3 + custom H2 fingerprint
with httpz.Client(
    ja3="771,4865-4867-...",
    h2_fingerprint="1:65536;...|15663105|0|m,s,a,p",
    browser="chrome",
) as c:
    print(c.get("https://example.com").status_code)

# 4. Async, with cookie persistence
async with httpz.AsyncClient() as c:
    await c.get("https://httpbin.org/cookies/set?session=abc")
    r = await c.get("https://httpbin.org/cookies")
    assert r.json()["cookies"]["session"] == "abc"
```

---

## Benchmarks

The `benchmarks/` directory compares httpz against `httpx`, `requests`, `curl_cffi`, `primp`, and `aiohttp` across four scenarios. Run it yourself with `python benchmarks/run_all.py`. The numbers below were measured against `httpbin.org` (which rate-limits aggressively — expect noise, especially in the long tails).

### Sequential GETs — 50 requests, one client

| Library            | Total (s) | req/s | mean (ms) | p95 (ms) | errors |
|--------------------|-----------|-------|-----------|----------|--------|
| requests           |     11.64 |   4.3 |     232.8 |    236.6 |      0 |
| curl_cffi          |     11.82 |   4.2 |     236.5 |    238.8 |      0 |
| httpx              |     11.86 |   4.2 |     237.2 |    241.6 |      0 |
| httpz_async        |     12.27 |   4.1 |     245.5 |    256.6 |      0 |
| aiohttp            |     12.31 |   4.1 |     246.2 |    248.8 |      0 |
| httpx_async        |     12.31 |   4.1 |     246.2 |    249.3 |      0 |
| **httpz**          | **12.37** | **4.0** | **247.3** | **259.3** | **0** |
| curl_cffi_async    |     12.56 |   4.0 |     251.1 |    256.2 |      0 |
| primp              |    182.16 |   0.2 |    3643.3 |  15008.8 |      7 |

Steady-state, everything is network-bound and clusters within ~10ms of each other. httpz adds ~15ms over the fastest sync client per request — a tiny price for the FFI hop into Go.

### Concurrent GETs — 50 requests, concurrency 10

| Library            | Total (s) | req/s | mean (ms) | p95 (ms) | errors |
|--------------------|-----------|-------|-----------|----------|--------|
| curl_cffi_async    |      1.50 |  33.4 |     273.7 |    476.5 |      0 |
| httpx_async        |      2.01 |  24.8 |     379.7 |   1001.9 |      0 |
| aiohttp            |      2.02 |  24.8 |     376.3 |   1018.4 |      0 |
| **httpz** (sync)   | **10.06** | **5.0** | **1952.3** | **3664.3** | **0** |
| httpx (sync)       |     10.74 |   4.7 |    1867.4 |   3382.3 |      0 |
| requests           |     22.77 |   2.2 |    3901.8 |   9821.8 |      0 |
| httpz_async        |     31.97 |   1.3 |    4960.7 |  15007.1 |     10 |
| primp              |     34.69 |   1.0 |    5756.2 |  15013.9 |     15 |
| curl_cffi          |     35.26 |   1.4 |    5363.4 |  13200.7 |      1 |

Sync httpz beats sync httpx and is **~2.3× faster than `requests`** under load. The native async clients (`aiohttp`, `httpx_async`, `curl_cffi_async`) win on throughput because their concurrency is in-process rather than thread-bounded. `httpz_async` ran into httpbin rate-limiting (10 timeouts) on this pass.

### Cold-start — 10 iterations of (construct + 1 GET)

| Library            | Total (s) | req/s | mean (ms) | p95 (ms) | errors |
|--------------------|-----------|-------|-----------|----------|--------|
| curl_cffi_async    |      7.25 |   1.4 |     725.3 |    754.1 |      0 |
| **httpz**          | **11.17** | **0.9** | **1117.1** | **1596.7** | **0** |
| aiohttp            |     12.21 |   0.8 |    1220.6 |   1863.9 |      0 |
| httpx              |     20.05 |   0.5 |    2004.5 |   3619.5 |      0 |
| requests           |     24.22 |   0.4 |    2421.5 |   3839.2 |      0 |
| httpx_async        |     31.67 |   0.3 |    3166.9 |  10184.0 |      1 |
| curl_cffi          |     33.41 |   0.3 |    3340.9 |   8017.2 |      0 |
| primp              |     36.25 |   0.3 |    3625.5 |   9521.1 |      0 |
| httpz_async        |     79.58 |   0.1 |    7957.9 |  15009.7 |      3 |

httpz comes in **second only to `curl_cffi_async`** for cold-start cost — better than `httpx`, `requests`, `primp`, and the sync `curl_cffi`. Useful if you spin up short-lived clients in a CLI or worker.

### Sequential POST + JSON — 50 requests

| Library            | Total (s) | req/s | mean (ms) | p95 (ms) | errors |
|--------------------|-----------|-------|-----------|----------|--------|
| primp              |     11.56 |   4.3 |     231.2 |    236.6 |      0 |
| httpz_async        |     11.83 |   4.2 |     236.5 |    250.2 |      0 |
| curl_cffi          |     11.87 |   4.2 |     237.5 |    247.8 |      0 |
| httpx              |     12.18 |   4.1 |     243.6 |    247.6 |      0 |
| **httpz**          | **12.22** | **4.1** | **244.3** | **253.1** | **0** |
| httpx_async        |     12.64 |   4.0 |     252.8 |    256.9 |      0 |
| requests           |    173.81 |   0.3 |    3476.1 |  15009.0 |      4 |
| curl_cffi_async    |    181.52 |   0.2 |    3630.4 |  15009.0 |      6 |
| aiohttp            |    202.47 |   0.2 |    4049.5 |  15616.0 |      5 |

httpz handles POST + JSON serialization within the same ~12s band as the other healthy clients. `requests`, `aiohttp`, and `curl_cffi_async` hit httpbin's POST rate limit hard on this pass.

### Takeaways

- **Steady-state per-request overhead** is essentially the network. All libraries that didn't get rate-limited finished within ~10 ms of each other per request.
- **Sync concurrency**: httpz outperforms `httpx` and is roughly 2.3× faster than `requests`.
- **Cold-start**: httpz is second only to `curl_cffi_async`, beating every other sync client and most async ones.
- **Async**: aiohttp / httpx_async / curl_cffi_async are the throughput kings for non-fingerprinted workloads.

If you need TLS fingerprint control, httpz is competitive on every axis — and the only Python library where you can hand it any JA3 string with no setup ceremony.

To reproduce: `python benchmarks/run_all.py` (or, for stable numbers, point it at a local server with `--url http://127.0.0.1:8000/`).

---

## Installation

```bash
pip install pyhttpz --upgrade
```

> The PyPI distribution name is **`pyhttpz`** (the bare `httpz` name was already taken on PyPI). The Python import name is unchanged — once installed, you still write `import httpz`.

The wheel ships with the prebuilt `httpz_bridge` shared library for Windows, Linux, and macOS.

---

## API Reference

### `httpz.Client`

A **synchronous, session-scoped HTTP client** with first-class TLS-fingerprint control. Modeled after `httpx.Client` so most existing httpx code ports over by changing the import.

Under the hood, every `Client` owns a session inside the Go-side `azuretls-client` runtime (reached via a thin CGO bridge). That session holds the TLS spec, HTTP/2 spec, cookie jar, default headers, proxy, and connection pool — so multiple requests through the same `Client` reuse connections and share cookie state, exactly like a `requests.Session` or `httpx.Client`. When you close the client (explicitly via `.close()`, by exiting a `with` block, or when it's garbage-collected) the Go-side session is torn down and its sockets are released.

**Construction**

```python
httpz.Client(
    *,
    headers=None,           # default headers for every request
    cookies=None,           # initial cookie jar (dict or httpz.Cookies)
    proxy=None,             # "http://...", "https://...", or "socks5://..."
    ja3=None,               # JA3 fingerprint string (requires `browser`)
    h2_fingerprint=None,    # Akamai-format HTTP/2 fingerprint
    browser=None,           # "chrome" | "firefox" | "safari" | "edge" | "opera" | "ios"
    user_agent=None,        # overrides the navigator's default UA
    impersonate=None,       # one-shot preset (e.g. "chrome131") — sets ja3+h2+UA+browser
    timeout=None,           # default request timeout, seconds (float)
    max_redirects=10,       # global cap on redirect chain length
    verify=True,            # set False to skip TLS cert validation (dev only)
)
```

| Argument | Type | What it does |
|---|---|---|
| `headers` | `dict \| list \| Headers` | Default headers merged into every request. Per-request `headers=` overrides on a key-by-key basis. |
| `cookies` | `dict \| Cookies` | Pre-populated cookie jar. Cookies sent by the server are added automatically. |
| `proxy` | `str` | Upstream proxy. Schemes: `http`, `https`, `socks5`. |
| `ja3` | `str` | JA3 client fingerprint — rewrites the TLS ClientHello to match. **Requires `browser=`.** |
| `h2_fingerprint` | `str` | Akamai HTTP/2 fingerprint — controls SETTINGS, WINDOW_UPDATE, pseudo-header order, and PRIORITY frames. |
| `browser` | `str` | Navigator family that backs the JA3/HTTP/2 stack. Module constants exist: `httpz.CHROME`, `FIREFOX`, `SAFARI`, `EDGE`, `OPERA`, `IOS`. |
| `user_agent` | `str` | Overrides the default `User-Agent`. |
| `impersonate` | `str` | Shorthand that resolves to a full preset (`ja3` + `h2_fingerprint` + `browser` + `user_agent`). Any other explicit kwarg you pass **still wins** over the preset. |
| `timeout` | `float` | Default per-request timeout in seconds. Per-request `timeout=` overrides. |
| `max_redirects` | `int` | Maximum redirect-chain length before raising `TooManyRedirects`. |
| `verify` | `bool` | When `False`, TLS certificate verification is skipped. Useful for self-signed certs in development; **never** ship `False` to production. |

**Lifecycle**

- Use as a context manager (`with httpz.Client() as c:`) — the session is closed on exit.
- Or call `.close()` explicitly. After `.close()` any further request raises `HTTPZError("Client is closed")`.
- A `__del__` finalizer attempts a best-effort cleanup if you forget — don't rely on it.

**HTTP methods**

All return a `httpz.Response`.

| Method | Signature |
|---|---|
| `client.request(method, url, **kw)` | Full-featured request — every other method is sugar over this. |
| `client.get(url, **kw)` | GET. |
| `client.post(url, **kw)` | POST. |
| `client.put(url, **kw)` | PUT. |
| `client.patch(url, **kw)` | PATCH. |
| `client.delete(url, **kw)` | DELETE. |
| `client.head(url, **kw)` | HEAD. |
| `client.options(url, **kw)` | OPTIONS. |

Shared `**kw` for every method:

| Keyword | Type | Meaning |
|---|---|---|
| `headers` | `dict \| list \| Headers` | Per-request headers (merged on top of client defaults; per-request keys win). |
| `params` | `dict[str, str]` | Query-string parameters; merged with any query string already on `url`. |
| `json` | `Any` | JSON-serialized into the body; sets `Content-Type: application/json`. |
| `data` | `dict \| str \| bytes` | Form data when `dict` (`application/x-www-form-urlencoded`); raw otherwise. |
| `content` | `bytes` | Raw request body for binary payloads. |
| `timeout` | `float` | Override the client-default timeout for this call only. |
| `follow_redirects` | `bool` | Defaults to `True`. Set `False` to surface 3xx responses directly. |
| `max_redirects` | `int` | Per-request redirect cap. |

**Configuration methods**

Reconfigure a *live* session without rebuilding it. Useful when rotating fingerprints or proxies between requests.

| Method | Purpose |
|---|---|
| `client.apply_ja3(ja3, browser)` | Replace the active JA3 fingerprint. |
| `client.apply_h2_fingerprint(fp)` | Replace the active HTTP/2 fingerprint. |
| `client.set_proxy(url)` | Route subsequent requests through a new proxy. |
| `client.clear_proxy()` | Stop using a proxy. |

**Attributes**

- `client.headers` — mutable `Headers` instance for the client's default headers (case-insensitive multi-dict).
- `client.cookies` — the session `Cookies` jar. Read after a response to inspect what the server set; mutate to inject your own.

**Example — everything together**

```python
import httpz

with httpz.Client(
    impersonate="chrome131",
    proxy="socks5://user:pass@127.0.0.1:1080",
    timeout=30.0,
    headers={"Accept-Language": "en-US,en;q=0.9"},
) as client:
    client.cookies["session"] = "abc123"
    r = client.get("https://api.example.com/me")
    r.raise_for_status()
    print(r.json())

    # Rotate the TLS fingerprint mid-session
    client.apply_ja3("771,4865-4867-...", browser="chrome")
    r2 = client.post("https://api.example.com/items", json={"name": "x"})
```

---

### `httpz.AsyncClient`

The **asyncio-friendly counterpart** to `Client`. Mirrors `httpx.AsyncClient` — same API surface, every I/O method is an `async def` that you `await`.

`AsyncClient` is implemented as a thin async wrapper around `Client`: it constructs a sync `Client` internally, and every request hops into a worker thread via `asyncio.to_thread` so the blocking CGO call never stalls the event loop. **The thread-pool hand-off means async throughput is bounded by `asyncio`'s default thread pool size** (typically `min(32, os.cpu_count() + 4)`) — fine for most workloads, but worth knowing if you're firing hundreds of concurrent requests. For raw event-loop-native concurrency on non-fingerprinted workloads, libraries like `aiohttp` or `httpx_async` will be faster (see the [Benchmarks](#benchmarks) section).

**Construction**

Takes **the exact same keyword arguments as `Client`** (see the table above) — they're forwarded verbatim.

```python
client = httpz.AsyncClient(
    impersonate="chrome131",
    proxy="http://127.0.0.1:8080",
    timeout=15.0,
)
```

**Lifecycle**

- Use as an async context manager: `async with httpz.AsyncClient() as c:` — the session is closed on exit.
- Or `await client.close()` explicitly.

**HTTP methods**

All `async`. All return a `httpz.Response`. Accept the same `**kw` as the sync client.

```python
await client.request(method, url, **kw)
await client.get(url, **kw)
await client.post(url, **kw)
await client.put(url, **kw)
await client.patch(url, **kw)
await client.delete(url, **kw)
await client.head(url, **kw)
await client.options(url, **kw)
```

**Configuration methods**

```python
await client.apply_ja3(ja3, browser)
await client.apply_h2_fingerprint(fp)
await client.set_proxy(url)
await client.clear_proxy()
```

**Attributes**

- `client.headers` — shared with the underlying sync client.
- `client.cookies` — shared with the underlying sync client.

**Example**

```python
import asyncio
import httpz

async def main():
    async with httpz.AsyncClient(impersonate="chrome131") as client:
        # Fan out 20 concurrent requests
        urls = [f"https://httpbin.org/anything/{i}" for i in range(20)]
        responses = await asyncio.gather(*(client.get(u) for u in urls))
        for r in responses:
            print(r.status_code, r.url)

asyncio.run(main())
```

---

## Credits

- **httpz** is written and maintained by **Shahzain345**.
- The async client design takes cues from **[aiohttp](https://github.com/aio-libs/aiohttp)** — credit to the aio-libs team for one of the best async HTTP libraries in any language; their work shaped how Python developers think about async HTTP.
- The TLS engine is **[azuretls-client](https://github.com/Noooste/azuretls-client)** by Noooste — httpz would not exist without it.
- API surface modeled after **[httpx](https://github.com/encode/httpx)**.

---

## License

MIT.

Copyright © 2026 **Shahzain345**. All rights reserved.

`httpz` is written and maintained by Shahzain345. See [Credits](#credits) for the upstream libraries it builds on.
