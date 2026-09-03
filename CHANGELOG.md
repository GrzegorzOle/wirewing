# Historia zmian

Format według [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie według [SemVer](https://semver.org/lang/pl/).

## [Niewydane]

### Do zrobienia przed 0.1.0

- [ ] Wstawić dosłowny tekst licencji: `python scripts/fetch_license.py`
- [ ] Uzupełnić cennik w `COMMERCIAL.md`
- [ ] Zlecić przegląd `CLA.md` kancelarii IP
- [ ] Sprawdzić nazwę „wirewing" w [TMview](https://www.tmdn.org/tmview/) i na PyPI
- [ ] Podmienić `OWNER` w `pyproject.toml` i `README.md` na nazwę konta GitHub
- [ ] Zastąpić referencyjne `MsgId` rzeczywistymi ID urządzenia

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
