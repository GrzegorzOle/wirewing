# Współpraca przy wirewing

Cieszę się, że chcesz pomóc. Kilka rzeczy, które warto wiedzieć zanim
otworzysz pull request.

## Zanim napiszesz kod

Otwórz issue i opisz, co chcesz zrobić. Dotyczy to zwłaszcza zmian w warstwie
protokołu — jeśli ktoś już nad tym pracuje albo masz inne urządzenie niż
zakładane, lepiej ustalić to przed napisaniem 400 linii.

## CLA — konieczne

Projekt jest licencjonowany podwójnie: niekomercyjnie za darmo, komercyjnie
odpłatnie. Żeby móc udzielić firmie licencji na kod, muszę mieć do niego prawa.
Dlatego każdy wkład wymaga podpisania [CLA](CLA.md) — bot poprosi cię o to
automatycznie przy pierwszym PR. Zachowujesz pełne prawa autorskie do swojego
kodu; udzielasz mi jedynie dodatkowej licencji.

Do literówek i poprawek w dokumentacji wystarczy DCO: `git commit -s`.

## Czego nie przyjmę

- **Zależności na GPL lub LGPL linkowanej statycznie.** Jedna taka biblioteka
  wywraca cały model licencyjny projektu, bo GPL wymaga wypuszczenia całości
  na warunkach zezwalających na komercję. MIT, BSD, Apache-2.0, ISC i PSF — tak.
  LGPL wyłącznie dynamicznie i po uzgodnieniu.
- **Kodu skopiowanego z zamkniętego firmware'u** ani zdekompilowanego. Analiza
  protokołu na poziomie ruchu na łączu jest w porządku i w UE wprost dozwolona
  (dyrektywa 2009/24/WE, art. 6); przeklejanie cudzego kodu — nie.
- **Zrzutów ruchu z prawdziwych urządzeń** bez usunięcia numerów seryjnych,
  identyfikatorów i danych lokalizacyjnych.

## Standard techniczny

```bash
pip install -e ".[dev]"

ruff format .          # formatowanie
ruff check .           # lint
mypy                   # typy, tryb strict
pytest --cov           # testy
```

Wszystko musi przechodzić przed merge. Poza tym:

- **Każdy nowy plik źródłowy zaczyna się od nagłówka SPDX:**
  `# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0`
- Kod publiczny ma pełne adnotacje typów — `mypy --strict` nie może zgłaszać uwag.
- Zmiana w warstwie protokołu wymaga testu na `LoopbackTransport`. Testy nie mogą
  wymagać podłączonego sprzętu.
- Zmiany widoczne dla użytkownika trafiają do `CHANGELOG.md`.
- Commity w formacie [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

## Testowanie na sprzęcie

Jeśli masz fizyczne urządzenie i weryfikujesz na nim zmianę, napisz w opisie PR
jaki to model, wersja firmware'u i parametry portu. To najcenniejsza informacja,
jaką możesz dołączyć — sam nie mam dostępu do każdego wariantu.

**Zawsze testuj ze zdjętymi śmigłami.**
