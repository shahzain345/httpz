"""Browser-impersonate presets.

Loads `_presets.json` (produced by scripts/scrape_fingerprints.py) and exposes
helpers used by Client/AsyncClient to resolve impersonate=... into a concrete
JA3 + Akamai (H2) fingerprint + User-Agent + browser navigator.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .exceptions import HTTPZError

_PRESETS_PATH = os.path.join(os.path.dirname(__file__), "_presets.json")

_DATA: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _DATA
    if _DATA is None:
        if not os.path.exists(_PRESETS_PATH):
            _DATA = {"targets": {}, "aliases": {}}
        else:
            with open(_PRESETS_PATH, "r", encoding="utf-8") as f:
                _DATA = json.load(f)
    return _DATA


def list_impersonate_targets() -> List[str]:
    """All preset names that can be passed as impersonate=."""
    data = _load()
    names = set(data.get("targets", {}).keys()) | set(data.get("aliases", {}).keys())
    return sorted(names)


def resolve_impersonate(name: str) -> Dict[str, Any]:
    """Return the preset dict for `name`, after resolving aliases.

    Raises HTTPZError if the name is unknown.
    """
    data = _load()
    targets = data.get("targets", {})
    aliases = data.get("aliases", {})

    if name in targets:
        return targets[name]
    if name in aliases:
        key = aliases[name]
        if key in targets:
            return targets[key]

    # Tolerant fallback: normalize (strip _ and .) and try again.
    norm = name.replace("_", "").replace(".", "").lower()
    if norm in aliases:
        key = aliases[norm]
        if key in targets:
            return targets[key]

    raise HTTPZError(
        f"Unknown impersonate target: {name!r}. "
        f"See httpz.list_impersonate_targets() for the {len(targets)} available presets."
    )
