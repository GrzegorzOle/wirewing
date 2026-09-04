# Historia zmian

Format według [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie według [SemVer](https://semver.org/lang/pl/).

## [Niewydane]

### Dodane

- `scripts/probe_link.py` — pasywne rozpoznanie protokołu urządzenia. Liczy
  ramki MAVLink v1/v2 i wirewing, weryfikując ich łańcuchowanie zamiast samych
  znaczników, identyfikuje płytę po VID:PID i nie wysyła na łącze ani bajtu.
- `scripts/check_dependencies.py` rozróżnia status `ACCEPTED` — świadomą decyzję
  licencyjną wraz z uzasadnieniem, raportowaną w zestawieniu licencji. Wpis na tej
  liście nie przesłania statusu `FORBIDDEN`. Pierwszym i jedynym wpisem jest
  `pathspec` (MPL-2.0), wciągany przez `hatchling` wyłącznie na czas budowania.
  Dzięki temu `--strict` przechodzi — nie ma już nierozstrzygniętych zależności.

### Zmienione

- `LICENSE.md` zawiera dosłowny tekst PolyForm Noncommercial 1.0.0 zamiast
  zaślepki. Job `license-file` w CI przechodzi.
- `COMMERCIAL.md` nie zawiera już szablonowego cennika z zaślepkami `X` i `Y`
  ani notatki roboczej widocznej publicznie. W fazie alfa licencje wyceniane są
  indywidualnie; regularny cennik pojawi się wraz z wersją 1.0. Zakres pakietów
  pozostaje opisany, bo model licencjonowania jest przemyślany — brakowało
  wyłącznie kwot, a te nie są warunkiem wydania 0.1.0.

- README opisuje warianty instalacji i wprost stwierdza, że `pymavlink` nie jest
  i nie będzie zależnością projektu — urządzenia mówiące MAVLinkiem obsługuje się
  osobno zainstalowaną biblioteką, poza wirewing.
- `docs/protocol.md` zawiera gotowy fragment do pasywnego rozpoznania, czy
  urządzenie mówi MAVLinkiem, zanim zacznie się odtwarzać protokół.
- `scripts/fetch_license.py` przy odrzuconym certyfikacie TLS wypisuje wyjaśnienie
  zamiast surowego stosu wywołań: wskazuje lokalne skanowanie HTTPS jako najczęstszą
  przyczynę, odradza wyłączanie weryfikacji i podaje trzy drogi wyjścia.

### Do zrobienia przed 0.1.0

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
