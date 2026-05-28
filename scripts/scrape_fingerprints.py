"""Scrape JA3 + Akamai (H2) fingerprints from curl_cffi and primp presets.

For each impersonate target exposed by curl_cffi and primp, this script makes a
real request through that library to https://tls.peet.ws/api/all, captures the
JA3 string + Akamai (HTTP/2) fingerprint string + User-Agent the server saw,
and writes everything to httpz/_presets.json.

That JSON is then consumed by httpz so users can write:

    httpz.Client(impersonate="chrome131")

and get exactly the TLS handshake that curl_cffi or primp produces for that
preset, without depending on curl_cffi or primp at runtime.

Usage:
    python scripts/scrape_fingerprints.py
    python scripts/scrape_fingerprints.py --only curl_cffi
    python scripts/scrape_fingerprints.py --skip primp --delay 0.5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import typing
from datetime import datetime, timezone

PROBE_URL = "https://tls.peet.ws/api/all"

OKHTTP_PREFIXES = ("okhttp",)  # Skipped: azuretls has no okhttp navigator preset.

# Family detection: name prefix -> azuretls browser navigator.
FAMILY_PREFIXES = [
    ("firefox", "firefox"),
    ("chrome",  "chrome"),
    ("edge",    "edge"),
    ("safari",  "safari"),
    ("tor",     "firefox"),  # tor browser is firefox-derived
]


def detect_family(name: str) -> str | None:
    n = name.lower()
    for prefix, family in FAMILY_PREFIXES:
        if n.startswith(prefix):
            return family
    return None


def curl_cffi_targets() -> list[str]:
    from curl_cffi.requests.impersonate import BrowserType
    return [t.value for t in BrowserType]


def primp_targets() -> list[str]:
    import primp.primp as _primp_native
    IMPERSONATE = getattr(_primp_native, "IMPERSONATE", None)
    if IMPERSONATE is not None and typing.get_origin(IMPERSONATE) is typing.Literal:
        return [v for v in typing.get_args(IMPERSONATE) if v != "random"]
    # Fallback: parse the .pyi
    import primp
    pyi = os.path.join(os.path.dirname(primp.__file__), "primp.pyi")
    with open(pyi, "r", encoding="utf-8") as f:
        text = f.read()
    block = text.split("IMPERSONATE = Literal[", 1)[1].split("]", 1)[0]
    out = []
    for tok in block.split(","):
        tok = tok.strip().strip('"').strip("'")
        if tok and tok != "random":
            out.append(tok)
    return out


def probe_with_curl_cffi(target: str, timeout: float):
    from curl_cffi import requests as cffi_req
    r = cffi_req.get(PROBE_URL, impersonate=target, timeout=timeout)
    return r.json()


def probe_with_primp(target: str, timeout: float):
    import primp
    client = primp.Client(impersonate=target, timeout=timeout)
    r = client.get(PROBE_URL)
    # primp Response has .text / .json
    body = r.text if hasattr(r, "text") else r.content.decode("utf-8")
    return json.loads(body) if isinstance(body, str) else body


def extract(payload: dict) -> dict:
    tls = payload.get("tls", {}) or {}
    h2 = payload.get("http2", {}) or {}
    return {
        "ja3": tls.get("ja3", ""),
        "ja3_hash": tls.get("ja3_hash", ""),
        "h2_fingerprint": h2.get("akamai_fingerprint", ""),
        "h2_fingerprint_hash": h2.get("akamai_fingerprint_hash", ""),
        "user_agent": payload.get("user_agent", ""),
    }


def scrape_source(source: str, targets: list[str], delay: float, timeout: float):
    out = {}
    probe = probe_with_curl_cffi if source == "curl_cffi" else probe_with_primp
    n = len(targets)
    print(f"[{source}] {n} targets to scrape")
    for i, t in enumerate(targets, 1):
        if any(t.startswith(p) for p in OKHTTP_PREFIXES):
            print(f"  ({i}/{n}) {t}: skipped (no azuretls navigator equivalent)")
            continue
        family = detect_family(t)
        if family is None:
            print(f"  ({i}/{n}) {t}: skipped (unknown browser family)")
            continue
        print(f"  ({i}/{n}) {t}: probing...", end="", flush=True)
        try:
            payload = probe(t, timeout)
            fp = extract(payload)
            if not fp["ja3"]:
                print(f" no JA3 in response, skipped")
                continue
            out[t] = {
                "source": source,
                "source_name": t,
                "browser": family,
                **fp,
            }
            print(f" ok (ja3_hash={fp['ja3_hash'][:16]})")
        except Exception as e:
            print(f" FAILED: {type(e).__name__}: {str(e)[:80]}")
        if delay:
            time.sleep(delay)
    return out


def dedupe_targets(targets: dict) -> tuple[dict, dict]:
    """Collapse targets that share the exact same (ja3, h2, user_agent).

    Returns (canonical_targets, alias_map). The alias map sends the dropped
    names to the canonical key so user lookups keep working.

    Canonical preference: curl_cffi over primp; within a source, the shortest
    name wins (e.g. `safari170` beats `safari17_0` beats `safari_17.0`).
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for name, p in targets.items():
        key = (p.get("ja3", ""), p.get("h2_fingerprint", ""), p.get("user_agent", ""))
        groups[key].append(name)

    def rank(name: str) -> tuple:
        source = targets[name].get("source", "")
        return (
            0 if source == "curl_cffi" else 1,
            len(name),
            name,
        )

    canonical = {}
    extra_aliases = {}
    for names in groups.values():
        names_sorted = sorted(names, key=rank)
        winner = names_sorted[0]
        canonical[winner] = targets[winner]
        for loser in names_sorted[1:]:
            extra_aliases[loser] = winner
    return canonical, extra_aliases


def build_aliases(targets: dict, extra_aliases: dict | None = None) -> dict:
    """Build a name->canonical-key alias map.

    Users want to write impersonate='chrome131' and have it match curl_cffi's
    'chrome131' or primp's 'chrome_131' interchangeably. Normalize by stripping
    underscores between letters and digits.
    """
    aliases = {}

    def norm(s: str) -> str:
        # "chrome_131" -> "chrome131", "safari_17.2.1" -> "safari1721",
        # "chrome_131_android" -> "chrome131android"
        return s.replace("_", "").replace(".", "").lower()

    # curl_cffi wins on collisions (newer, broader version set).
    order = sorted(targets.keys(), key=lambda k: 0 if targets[k]["source"] == "curl_cffi" else 1)
    for key in order:
        n = norm(key)
        aliases.setdefault(n, key)
        aliases.setdefault(key, key)

    # Names that lost the dedupe race still resolve to the canonical winner.
    if extra_aliases:
        for losing_name, winning_name in extra_aliases.items():
            aliases[losing_name] = winning_name
            aliases[norm(losing_name)] = winning_name
    return aliases


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--only", nargs="+", choices=["curl_cffi", "primp"])
    p.add_argument("--skip", nargs="+", default=[], choices=["curl_cffi", "primp"])
    p.add_argument("--delay", type=float, default=0.4,
                   help="Seconds between probes (be polite to tls.peet.ws)")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--out", default=None,
                   help="Output path (default: httpz/_presets.json)")
    args = p.parse_args()

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = args.out or os.path.join(here, "httpz", "_presets.json")

    sources = ["curl_cffi", "primp"]
    if args.only:
        sources = [s for s in sources if s in args.only]
    sources = [s for s in sources if s not in args.skip]

    targets = {}
    for src in sources:
        try:
            if src == "curl_cffi":
                names = curl_cffi_targets()
            else:
                names = primp_targets()
        except Exception as e:
            print(f"[{src}] could not list targets: {e}")
            continue
        scraped = scrape_source(src, names, args.delay, args.timeout)
        # Source-tagged key to avoid collisions when both libs have the same name.
        for k, v in scraped.items():
            stored_key = k if k not in targets else f"{src}:{k}"
            targets[stored_key] = v

    deduped, extra_aliases = dedupe_targets(targets)
    dropped = len(targets) - len(deduped)
    if dropped:
        print(f"Deduped {dropped} identical preset(s); {len(deduped)} unique profiles remain")

    aliases = build_aliases(deduped, extra_aliases)

    out = {
        "version": 1,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "probe_url": PROBE_URL,
        "targets": deduped,
        "aliases": aliases,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    print()
    print(f"Wrote {len(targets)} targets to {out_path}")


if __name__ == "__main__":
    main()
