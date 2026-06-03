"""Scrape JA3 + Akamai (H2) fingerprints from curl_cffi, primp and wreq presets.

For each impersonate target exposed by curl_cffi, primp and wreq, this script
makes a real request through that library to https://tls.peet.ws/api/all,
captures the JA3 string + Akamai (HTTP/2) fingerprint string + User-Agent the
server saw, and writes everything to httpz/presets.py as an embedded Python dict.

That embedded data is then consumed by httpz so users can write:

    httpz.Client(impersonate="chrome131")

and get exactly the TLS handshake that the source library produces for that
preset, without depending on that library at runtime.

Usage:
    # Full rebuild from curl_cffi + primp + wreq (drops manual entries):
    python scripts/scrape_fingerprints.py

    # Add ONLY new fingerprints from wreq on top of the existing presets.py,
    # skipping any whose (ja3, h2, user-agent) already exists. Preserves every
    # existing target, alias and manual entry:
    python scripts/scrape_fingerprints.py --augment --only wreq

    python scripts/scrape_fingerprints.py --only curl_cffi
    python scripts/scrape_fingerprints.py --skip primp --delay 0.5
"""
from __future__ import annotations

import argparse
import json
import os
import pprint
import sys
import time
import typing
from datetime import datetime, timezone

PROBE_URL = "https://tls.peet.ws/api/all"

OKHTTP_PREFIXES = ("okhttp",)  # Skipped: azuretls has no okhttp navigator preset.

# Family detection: name prefix -> azuretls browser navigator.
# Order matters: more specific prefixes (edge, opera) must come before the
# chromium families they would otherwise be mistaken for.
FAMILY_PREFIXES = [
    ("firefox", "firefox"),
    ("edge",    "edge"),
    ("opera",   "opera"),
    ("chrome",  "chrome"),
    ("safari",  "safari"),
    ("tor",     "firefox"),  # tor browser is firefox-derived
]


def _norm(s: str) -> str:
    """Normalize a preset name for alias lookup: drop `_`/`.` and lowercase.

    "chrome_131" -> "chrome131", "safari_17.2.1" -> "safari1721".
    """
    return s.replace("_", "").replace(".", "").lower()


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


def wreq_targets() -> list[str]:
    # The native Profile type isn't an iterable Enum, but every profile is
    # exposed as a (non-callable) class attribute on Emulation.
    from wreq import Emulation
    return [
        n for n in dir(Emulation)
        if not n.startswith("_") and not callable(getattr(Emulation, n))
    ]


def list_targets(source: str) -> list[str]:
    return {
        "curl_cffi": curl_cffi_targets,
        "primp": primp_targets,
        "wreq": wreq_targets,
    }[source]()


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


def probe_with_wreq(target: str, timeout: float):
    import asyncio
    import datetime as _dt
    import wreq
    from wreq.emulation import Profile

    profile = getattr(Profile, target)

    async def _go():
        client = wreq.Client(
            emulation=profile,
            timeout=_dt.timedelta(seconds=timeout or 20),
        )
        try:
            r = await client.get(PROBE_URL)
            body = await r.text()
        finally:
            try:
                client.close()
            except Exception:
                pass
        return json.loads(body)

    return asyncio.run(_go())


# HTTP/2 SETTINGS name -> id (RFC 7540 §6.5.2, 8441 §3, 9218 §2.1).
_H2_SETTING_IDS = {
    "HEADER_TABLE_SIZE": 1,
    "ENABLE_PUSH": 2,
    "MAX_CONCURRENT_STREAMS": 3,
    "INITIAL_WINDOW_SIZE": 4,
    "MAX_FRAME_SIZE": 5,
    "MAX_HEADER_LIST_SIZE": 6,
    "ENABLE_CONNECT_PROTOCOL": 8,
    "NO_RFC7540_PRIORITIES": 9,
}


def _repair_akamai(akamai: str, payload: dict) -> str:
    """Fix a tls.peet.ws quirk: it renders some SETTINGS ids it doesn't know
    (notably 8, ENABLE_CONNECT_PROTOCOL, which Safari 18.x sends) with a blank
    id, e.g. ``…;:1;…``. azuretls rejects an empty setting id, so when we see a
    blank-id token, rebuild the SETTINGS section from the raw SETTINGS frame
    (which carries the setting *names*) using the name->id map above. The other
    fields (window update | priority | header order) are kept verbatim, and
    well-formed fingerprints are returned untouched.
    """
    if not akamai:
        return akamai
    parts = akamai.split("|")
    tokens = parts[0].split(";") if parts[0] else []
    if not any(t.split(":", 1)[0] == "" for t in tokens):
        return akamai  # nothing malformed

    h2 = payload.get("http2", {}) or {}
    rebuilt = []
    for frame in h2.get("sent_frames", []):
        if frame.get("frame_type") != "SETTINGS":
            continue
        for entry in frame.get("settings", []):  # e.g. "ENABLE_CONNECT_PROTOCOL = 1"
            if "=" not in entry:
                continue
            name, value = (x.strip() for x in entry.split("=", 1))
            sid = _H2_SETTING_IDS.get(name)
            if sid is not None:
                rebuilt.append(f"{sid}:{value}")
        break
    if not rebuilt:
        return akamai  # couldn't rebuild — leave as-is rather than corrupt it
    parts[0] = ";".join(rebuilt)
    return "|".join(parts)


def extract(payload: dict) -> dict:
    tls = payload.get("tls", {}) or {}
    h2 = payload.get("http2", {}) or {}
    return {
        "ja3": tls.get("ja3", ""),
        "ja3_hash": tls.get("ja3_hash", ""),
        "h2_fingerprint": _repair_akamai(h2.get("akamai_fingerprint", ""), payload),
        "h2_fingerprint_hash": h2.get("akamai_fingerprint_hash", ""),
        "user_agent": payload.get("user_agent", ""),
    }


def scrape_source(source: str, targets: list[str], delay: float, timeout: float):
    out = {}
    probe = {
        "curl_cffi": probe_with_curl_cffi,
        "primp": probe_with_primp,
        "wreq": probe_with_wreq,
    }[source]
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

    # curl_cffi wins on collisions (newer, broader version set).
    order = sorted(targets.keys(), key=lambda k: 0 if targets[k]["source"] == "curl_cffi" else 1)
    for key in order:
        n = _norm(key)
        aliases.setdefault(n, key)
        aliases.setdefault(key, key)

    # Names that lost the dedupe race still resolve to the canonical winner.
    if extra_aliases:
        for losing_name, winning_name in extra_aliases.items():
            aliases[losing_name] = winning_name
            aliases[_norm(losing_name)] = winning_name
    return aliases


def load_existing_presets(path: str) -> dict:
    """Parse the embedded `_DATA` dict out of an existing httpz/presets.py.

    Done by literal-eval of just the assignment so we don't need to import the
    whole httpz package (and its native bridge) to read the presets.
    """
    import ast

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    marker = "_DATA: Dict[str, Any] = "
    start = text.index(marker) + len(marker)
    end = text.index("\n\n\ndef ", start)
    return ast.literal_eval(text[start:end])


def augment(existing: dict, scraped: dict) -> dict:
    """Add only NEW fingerprints from `scraped` on top of `existing` presets.

    A scraped profile is "new" when its (ja3, h2_fingerprint, user_agent) tuple
    isn't already present in the existing targets (or in another scraped profile
    we already kept). Duplicates are dropped rather than stored a second time --
    their name is still wired up as an alias to the existing canonical profile
    when that name is otherwise unused. Existing targets, aliases and manual
    entries are preserved untouched.
    """
    targets = dict(existing.get("targets", {}))
    aliases = dict(existing.get("aliases", {}))

    def fp_key(p: dict) -> tuple:
        return (p.get("ja3", ""), p.get("h2_fingerprint", ""), p.get("user_agent", ""))

    fp_to_name = {}
    for name, p in targets.items():
        fp_to_name.setdefault(fp_key(p), name)

    def taken(name: str) -> bool:
        return name in targets or name in aliases

    def unique_name(base: str) -> str:
        # Follow the project's existing variant convention (e.g. "chrome133a").
        if not taken(base):
            return base
        for suffix in "abcdefghijklmnopqrstuvwxyz":
            if not taken(base + suffix):
                return base + suffix
        i = 2
        while taken(f"{base}{i}"):
            i += 1
        return f"{base}{i}"

    added = dropped = 0
    for raw_name in sorted(scraped.keys()):
        p = scraped[raw_name]
        key = fp_key(p)
        base = _norm(p.get("source_name", raw_name)) or raw_name.lower()

        if key in fp_to_name:
            dropped += 1
            canonical = fp_to_name[key]
            if not taken(base):
                aliases[base] = canonical
            continue

        name = unique_name(base)
        targets[name] = {
            "browser": p["browser"],
            "ja3": p["ja3"],
            "ja3_hash": p["ja3_hash"],
            "h2_fingerprint": p["h2_fingerprint"],
            "h2_fingerprint_hash": p["h2_fingerprint_hash"],
            "source": p["source"],
            "source_name": p["source_name"],
            "user_agent": p["user_agent"],
        }
        fp_to_name[key] = name
        aliases.setdefault(name, name)
        aliases.setdefault(_norm(name), name)
        added += 1

    print(f"Augment: +{added} new fingerprint(s), {dropped} duplicate(s) skipped")

    out = dict(existing)
    out["targets"] = targets
    out["aliases"] = aliases
    out["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return out


def render_presets_module(data: dict) -> str:
    """Render httpz/presets.py with `data` embedded as a Python dict literal.

    The preset data is inlined into the module (rather than shipped as a
    separate _presets.json) so compiled/bundled builds pick it up automatically.
    """
    literal = pprint.pformat(data, indent=4, width=100, sort_dicts=True)
    return (
        '"""Browser-impersonate presets.\n\n'
        "Resolves impersonate=... into a concrete JA3 + Akamai (H2) fingerprint +\n"
        "User-Agent + browser navigator.\n\n"
        "The preset data below is embedded directly in this module (regenerate with\n"
        "scripts/scrape_fingerprints.py). It used to live in a separate _presets.json\n"
        "data file; inlining it means compiled/bundled builds (PyInstaller, py2exe,\n"
        "zipapp, etc.) pick up the presets automatically with no extra data files.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, Dict, List\n\n"
        "from .exceptions import HTTPZError\n\n\n"
        "_DATA: Dict[str, Any] = " + literal + "\n\n\n"
        "def list_impersonate_targets() -> List[str]:\n"
        '    """All preset names that can be passed as impersonate=."""\n'
        '    names = set(_DATA.get("targets", {}).keys()) | set(_DATA.get("aliases", {}).keys())\n'
        "    return sorted(names)\n\n\n"
        "def resolve_impersonate(name: str) -> Dict[str, Any]:\n"
        '    """Return the preset dict for `name`, after resolving aliases.\n\n'
        "    Raises HTTPZError if the name is unknown.\n"
        '    """\n'
        '    targets = _DATA.get("targets", {})\n'
        '    aliases = _DATA.get("aliases", {})\n\n'
        "    if name in targets:\n"
        "        return targets[name]\n"
        "    if name in aliases:\n"
        "        key = aliases[name]\n"
        "        if key in targets:\n"
        "            return targets[key]\n\n"
        "    # Tolerant fallback: normalize (strip _ and .) and try again.\n"
        '    norm = name.replace("_", "").replace(".", "").lower()\n'
        "    if norm in aliases:\n"
        "        key = aliases[norm]\n"
        "        if key in targets:\n"
        "            return targets[key]\n\n"
        "    raise HTTPZError(\n"
        '        f"Unknown impersonate target: {name!r}. "\n'
        '        f"See httpz.list_impersonate_targets() for the {len(targets)} available presets."\n'
        "    )\n"
    )


def render_types_module(data: dict) -> str:
    """Render httpz/_types.py with a ``BrowserTypeLiteral`` of every valid name.

    Like curl_cffi's ``BrowserType``, this lets type checkers and IDEs
    validate/autocomplete ``impersonate=`` against the real set of presets.
    Includes both canonical target names and aliases (everything that resolves).
    """
    names = sorted(
        set(data.get("targets", {}).keys()) | set(data.get("aliases", {}).keys())
    )
    body = ",\n".join(f"    {name!r}" for name in names)
    return (
        '"""Static typing helpers for httpz (auto-generated).\n\n'
        "``BrowserTypeLiteral`` enumerates every string accepted by ``impersonate=``\n"
        "so type checkers and editors validate and autocomplete the value, the same\n"
        "way curl_cffi's ``BrowserType`` does. Regenerate with\n"
        "scripts/scrape_fingerprints.py.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from typing import Literal\n\n"
        f"# {len(names)} names ({len(data.get('targets', {}))} unique profiles + aliases).\n"
        "BrowserTypeLiteral = Literal[\n"
        f"{body},\n"
        "]\n"
    )


ALL_SOURCES = ["curl_cffi", "primp", "wreq"]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--only", nargs="+", choices=ALL_SOURCES)
    p.add_argument("--skip", nargs="+", default=[], choices=ALL_SOURCES)
    p.add_argument("--augment", action="store_true",
                   help="Add only NEW fingerprints from the scraped source(s) on "
                        "top of the existing presets.py, skipping any whose "
                        "(ja3, h2, user-agent) already exists. Preserves existing "
                        "targets, aliases and manual entries. (Use with --only wreq.)")
    p.add_argument("--delay", type=float, default=0.4,
                   help="Seconds between probes (be polite to tls.peet.ws)")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--out", default=None,
                   help="Output path (default: httpz/presets.py)")
    args = p.parse_args()

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = args.out or os.path.join(here, "httpz", "presets.py")

    sources = list(ALL_SOURCES)
    if args.only:
        sources = [s for s in sources if s in args.only]
    sources = [s for s in sources if s not in args.skip]

    targets = {}
    for src in sources:
        try:
            names = list_targets(src)
        except Exception as e:
            print(f"[{src}] could not list targets: {e}")
            continue
        scraped = scrape_source(src, names, args.delay, args.timeout)
        # Source-tagged key to avoid collisions when libs share the same name.
        for k, v in scraped.items():
            stored_key = k if k not in targets else f"{src}:{k}"
            targets[stored_key] = v

    if args.augment:
        existing = load_existing_presets(out_path)
        out = augment(existing, targets)
    else:
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
        f.write(render_presets_module(out))

    # Keep the BrowserTypeLiteral in sync with the presets.
    types_path = os.path.join(os.path.dirname(out_path), "_types.py")
    with open(types_path, "w", encoding="utf-8") as f:
        f.write(render_types_module(out))

    print()
    print(f"Wrote {len(out['targets'])} targets to {out_path}")
    print(f"Wrote BrowserTypeLiteral to {types_path}")


if __name__ == "__main__":
    main()
