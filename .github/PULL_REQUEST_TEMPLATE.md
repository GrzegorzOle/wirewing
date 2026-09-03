## Co zmienia ten PR

<!-- Krótko: co i dlaczego. Jeśli jest powiązane issue, podlinkuj: Fixes #123 -->

## Rodzaj zmiany

- [ ] Poprawka błędu
- [ ] Nowa funkcjonalność
- [ ] Zmiana łamiąca kompatybilność
- [ ] Dokumentacja
- [ ] Utrzymanie / refaktoryzacja

## Lista kontrolna

- [ ] Podpisałem [CLA](../CLA.md) (bot poprosi automatycznie przy pierwszym PR)
- [ ] `ruff check .` i `ruff format --check .` przechodzą
- [ ] `mypy` przechodzi bez uwag
- [ ] `pytest` przechodzi; dodałem test na zmienione zachowanie
- [ ] Nowe pliki `.py` mają nagłówek `# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0`
- [ ] **Nie dodałem zależności na GPL/AGPL ani LGPL linkowanej statycznie**
- [ ] Zmiany widoczne dla użytkownika są w `CHANGELOG.md`

## Testy na sprzęcie

<!-- Jeśli testowałeś na fizycznym urządzeniu: model, wersja firmware'u,
     parametry portu. To najcenniejsza informacja w całym PR. -->

- [ ] Testowane wyłącznie na `LoopbackTransport` (bez sprzętu)
- [ ] Testowane na fizycznym urządzeniu — **ze zdjętymi śmigłami**

Model / firmware / port:
