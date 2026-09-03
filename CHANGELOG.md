# Historia zmian

Format według [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie według [SemVer](https://semver.org/lang/pl/).

## [Niewydane]

### Dodane

- Zależność opcjonalna `wirewing[mavlink]` (`pymavlink`) dla urządzeń mówiących
  MAVLinkiem. Instalacja domyślna i `wirewing[serial]` pozostają bez niej.
- `scripts/probe_link.py` — pasywne rozpoznanie protokołu urządzenia. Liczy
  ramki MAVLink v1/v2 i wirewing, weryfikując ich łańcuchowanie zamiast samych
  znaczników, identyfikuje płytę po VID:PID i nie wysyła na łącze ani bajtu.
- `scripts/check_dependencies.py` rozróżnia teraz status `ACCEPTED` — świadomą
  decyzję licencyjną wraz z uzasadnieniem, raportowaną w zestawieniu licencji.
  Wpis na tej liście nie przesłania statusu `FORBIDDEN`.

### Zmienione

- README opisuje warianty instalacji i konsekwencje licencyjne extra `mavlink`
  (`pymavlink` jest na LGPL-3.0, w odróżnieniu od pozostałych zależności).
- `docs/protocol.md` zawiera gotowy fragment do pasywnego rozpoznania, czy
  urządzenie mówi MAVLinkiem, zanim zacznie się odtwarzać protokół.

### Do zrobienia przed 0.1.0

- [ ] Wstawić dosłowny tekst licencji: `python scripts/fetch_license.py`
- [ ] Uzupełnić cennik w `COMMERCIAL.md`
- [ ] Zlecić przegląd `CLA.md` kancelarii IP
- [ ] Sprawdzić nazwę „wirewing" w [TMview](https://www.tmdn.org/tmview/) i na PyPI
- [ ] Podmienić `OWNER` w `pyproject.toml` i `README.md` na nazwę konta GitHub
- [ ] Zastąpić referencyjne `MsgId` rzeczywistymi ID urządzenia
- [ ] Napisać warstwę integracyjną z MAVLinkiem — extra `mavlink` udostępnia
      na razie samą zależność, bez kodu
- [ ] Rozstrzygnąć `pathspec` (MPL-2.0, wciągany przez `hatchling`) — zależność
      wyłącznie build-time, nie jest dystrybuowana z pakietem

## [0.1.0] — nie wydano

### Dodane

- Transport szeregowy oparty o `pyserial` z konfiguracją prędkości, parzystości
  i sterowania przepływem.
- `LoopbackTransport` — atrapa łącza umożliwiająca testy bez sprzętu.
- Ramkowanie z sumą kontrolną CRC-16/CCITT-FALSE.
- `FrameParser` — parser strumieniowy z automatyczną resynchronizacją po
  przekłamaniu, licznikami błędów CRC i ochroną przed rozrostem bufora.
- `Link` — wątek odbiorczy, numeracja sekwencji, dopasowywanie ACK/NAK,
  ponawianie komend, cykliczny heartbeat, subskrypcje wiadomości.
- CLI `wirewing` z podkomendami `ports`, `monitor`, `status`, `send`.
- CI: testy na 4 wersjach Pythona i 3 systemach, lint, typy w trybie strict,
  blokada zależności na GPL/AGPL, weryfikacja nagłówków SPDX i kompletności
  pliku licencji.
