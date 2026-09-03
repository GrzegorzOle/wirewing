#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Wykryj zależności o licencjach niezgodnych z modelem licencyjnym wirewing.

Jedna biblioteka na GPL wciągnięta przez przypadek unieważnia cały model
podwójnego licencjonowania: GPL wymaga rozpowszechniania całości na warunkach
zezwalających na użycie komercyjne, czego licencja niekomercyjna nie robi.
Ten skrypt pilnuje, żeby taka zależność nie weszła niezauważona.

    python scripts/check_dependencies.py
    python scripts/check_dependencies.py --format markdown > THIRD_PARTY_LICENSES.md
"""

from __future__ import annotations

import argparse
import re
import sys
from importlib import metadata

# Licencje, które wykluczają model komercyjny — build musi na nich paść.
FORBIDDEN = (
    r"\bGNU General Public License\b",
    r"\bGPL-?[23]",
    r"\bGPLv[23]",
    r"\bAGPL",
    r"\bAffero\b",
    r"\bSSPL\b",
    r"\bCC-BY-NC\b",
)

# Licencje wymagające ręcznej decyzji (LGPL wolno, ale tylko dynamicznie).
REVIEW = (r"\bLGPL", r"\bLesser General Public\b", r"\bMPL-?2", r"\bMozilla Public\b")

# Bezpieczne, permisywne licencje.
ALLOWED = (
    r"\bMIT\b",
    r"\bBSD\b",
    r"\bApache\b",
    r"\bISC\b",
    r"\bPSF\b",
    r"\bPython Software Foundation\b",
    r"\bZlib\b",
    r"\bUnlicense\b",
    r"\bCC0\b",
    r"\bPolyForm\b",
)

# Pakiety należące do samego projektu lub do środowiska deweloperskiego,
# które nie są dystrybuowane razem z produktem.
IGNORED = {"wirewing", "pip", "setuptools", "wheel"}


def _license_of(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    parts: list[str] = []

    expression = meta.get("License-Expression")
    if expression:
        parts.append(str(expression))

    declared = meta.get("License")
    if declared and len(str(declared)) < 200:
        parts.append(str(declared))

    parts.extend(
        c.rsplit("::", 1)[-1].strip()
        for c in meta.get_all("Classifier") or []
        if str(c).startswith("License ::")
    )

    unique = list(dict.fromkeys(p for p in parts if p and p.upper() != "UNKNOWN"))
    return "; ".join(unique) if unique else "UNKNOWN"


def _classify(license_text: str) -> str:
    if any(re.search(p, license_text, re.I) for p in FORBIDDEN):
        return "FORBIDDEN"
    if any(re.search(p, license_text, re.I) for p in REVIEW):
        return "REVIEW"
    if any(re.search(p, license_text, re.I) for p in ALLOWED):
        return "OK"
    return "UNKNOWN"


def collect() -> list[tuple[str, str, str, str]]:
    rows = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or ""
        if not name or name.lower() in IGNORED:
            continue
        license_text = _license_of(dist)
        rows.append((name, dist.version or "?", license_text, _classify(license_text)))
    return sorted(set(rows), key=lambda r: r[0].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["text", "markdown"], default="text")
    parser.add_argument("--strict", action="store_true", help="traktuj UNKNOWN i REVIEW jako błąd")
    args = parser.parse_args()

    rows = collect()
    forbidden = [r for r in rows if r[3] == "FORBIDDEN"]
    review = [r for r in rows if r[3] in ("REVIEW", "UNKNOWN")]

    if args.format == "markdown":
        print("# Licencje zależności\n")
        print("| Pakiet | Wersja | Licencja | Status |")
        print("|---|---|---|---|")
        for name, version, lic, status in rows:
            print(f"| {name} | {version} | {lic} | {status} |")
    else:
        width = max((len(r[0]) for r in rows), default=10)
        for name, version, lic, status in rows:
            print(f"{status:<10} {name:<{width}} {version:<12} {lic}")

    print(file=sys.stderr)
    if forbidden:
        print("BŁĄD: zależności o licencjach niezgodnych z modelem projektu:", file=sys.stderr)
        for name, version, lic, _ in forbidden:
            print(f"  - {name} {version}: {lic}", file=sys.stderr)
        print("\nUsuń je albo zastąp odpowiednikiem na MIT/BSD/Apache.", file=sys.stderr)
        return 1

    if review:
        print("UWAGA: wymagają ręcznej decyzji:", file=sys.stderr)
        for name, version, lic, status in review:
            print(f"  - [{status}] {name} {version}: {lic}", file=sys.stderr)
        if args.strict:
            return 1

    if not forbidden and not review:
        print("OK: wszystkie zależności mają licencje permisywne.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
