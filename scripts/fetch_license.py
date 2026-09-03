#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Pobierz kanoniczny tekst PolyForm Noncommercial 1.0.0 i wstaw go do LICENSE.md.

Skrypt celowo nie zawiera tekstu licencji „na sztywno" — pobiera go zawsze
ze źródła, żeby nie dało się przypadkiem opublikować przekłamanej wersji.

    python scripts/fetch_license.py           # wstaw do LICENSE.md
    python scripts/fetch_license.py --check   # tylko sprawdź (kod wyjścia dla CI)
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://polyformproject.org/licenses/noncommercial/1.0.0/"
ROOT = Path(__file__).resolve().parent.parent
LICENSE_FILE = ROOT / "LICENSE.md"

BEGIN = "<!-- ▼▼▼ WKLEJ TUTAJ DOSŁOWNY TEKST PolyForm Noncommercial 1.0.0 ▼▼▼ -->"
END = "<!-- ▲▲▲ KONIEC TEKSTU LICENCJI ▲▲▲ -->"

PLACEHOLDER = "Tekst licencji nie został jeszcze wstawiony"

# Zdania-kotwice, które muszą wystąpić w poprawnie pobranym tekście.
SANITY_MARKERS = (
    "PolyForm Noncommercial License 1.0.0",
    "Acceptance",
    "Copyright License",
    "Patent License",
    "Noncommercial Purposes",
    "No Liability",
    "Definitions",
)


def _html_to_text(html: str) -> str:
    body = re.sub(r"(?is).*?<body[^>]*>", "", html)
    body = re.sub(r"(?is)</body>.*", "", body)
    body = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", "", body)
    body = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n\n", body)
    body = re.sub(r"(?i)<br\s*/?>", "\n", body)
    body = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", body)
    body = re.sub(r"<[^>]+>", "", body)

    for entity, char in (
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
        ("&nbsp;", " "),
    ):
        body = body.replace(entity, char)

    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return "\n".join(line.strip() for line in body.splitlines()).strip()


def fetch() -> str:
    with urllib.request.urlopen(URL, timeout=30) as response:
        html = response.read().decode("utf-8")
    text = _html_to_text(html)

    missing = [marker for marker in SANITY_MARKERS if marker not in text]
    if missing:
        raise SystemExit(
            "Pobrany tekst nie wygląda na kompletną licencję — brakuje sekcji: "
            + ", ".join(missing)
            + f"\nPobierz ją ręcznie z {URL} i wklej do LICENSE.md."
        )
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="tylko weryfikuj, nic nie zapisuj")
    args = parser.parse_args()

    current = LICENSE_FILE.read_text(encoding="utf-8")

    if args.check:
        if PLACEHOLDER in current:
            print(
                "BŁĄD: LICENSE.md wciąż zawiera zaślepkę zamiast tekstu licencji.",
                file=sys.stderr,
            )
            print("Uruchom: python scripts/fetch_license.py", file=sys.stderr)
            return 1
        missing = [m for m in SANITY_MARKERS if m not in current]
        if missing:
            print(f"BŁĄD: w LICENSE.md brakuje sekcji: {', '.join(missing)}", file=sys.stderr)
            return 1
        print("OK: LICENSE.md zawiera kompletny tekst licencji.")
        return 0

    if BEGIN not in current or END not in current:
        print("BŁĄD: nie znaleziono znaczników wstawiania w LICENSE.md.", file=sys.stderr)
        return 1

    licence_text = fetch()
    head = current.split(BEGIN)[0]
    tail = current.split(END)[1]
    LICENSE_FILE.write_text(f"{head}{BEGIN}\n\n{licence_text}\n\n{END}{tail}", encoding="utf-8")
    print(f"Wstawiono tekst licencji do {LICENSE_FILE} ({len(licence_text)} znaków).")
    print("Porównaj wynik ze stroną źródłową przed commitem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
