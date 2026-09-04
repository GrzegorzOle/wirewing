# Historia zmian

Format według [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie według [SemVer](https://semver.org/lang/pl/).

## [Niewydane]

### Dodane

- `wirewing.mavlink` — natywny koder i dekoder MAVLink, bez zależności
  zewnętrznych. Dekoduje v1 i v2, koduje v1, weryfikuje sumy kontrolne z bajtem
  `CRC_EXTRA` i odwzorowuje komendy na `COMMAND_LONG`. Zweryfikowany wobec ramki
  przechwyconej z rzeczywistego kontrolera, więc test wykrywa błąd w CRC albo
  w tablicy `CRC_EXTRA`, którego sprawdzenie „zakoduj i zdekoduj" by przepuściło.
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

- [x] ~~Sprawdzić nazwę „wirewing" na PyPI~~ — wolna (`wirewing` i `wire-wing`,
      HTTP 404 z API PyPI)
- [x] ~~Sprawdzić nazwę „wirewing" w TMview~~ — brak trafień przy operatorze
      „Zawiera", we wszystkich urzędach i klasach. Uwaga: to wyszukiwanie
      tekstowe, nie badanie podobieństwa. Formy dwuczłonowe (`WIRE & WING`,
      rej. USA 5976778) i zbliżone fonetycznie (`WIRENG`, rej. USA 3910211,
      anteny i sprzęt telekomunikacyjny) nie zawierają tego ciągu i w tym
      zapytaniu się nie pojawiają
- [x] ~~Podmienić `OWNER` w `pyproject.toml` i `README.md`~~ — `GrzegorzOle`
- [ ] Zastąpić referencyjne `MsgId` rzeczywistymi ID urządzenia

### Odłożone — poza bramką 0.1.0

Projekt jest prototypem, a ten kod jest jednym z jego składników. Poniższe
sprawy stają się istotne dopiero przy komercjalizacji i nie blokują wydania.

- [ ] Przegląd `CLA.md` kancelarią IP — potrzebny przed przyjęciem pierwszego
      zewnętrznego wkładu, nie wcześniej
- [ ] **Rozstrzygnąć kolizję z EUTM `WingWire`** (EUIPO 019286909, zgłoszony
      04/12/2025, zarejestrowany, klasy **9 i 42**, Manzke Tobias). Te same dwa
      człony słowne w odwrotnej kolejności, w identycznych klasach, na rynku UE.
      Znaleziony zapytaniem `wire wing` w TMview — zapytanie o `wirewing` go nie
      pokazuje, bo nie zawiera tego ciągu.
      Do zlecenia kancelarii razem z przeglądem `CLA.md`: ocena podobieństwa oraz
      ryzyka sprzeciwu przy komercyjnym używaniu nazwy. Przed decyzją warto
      otworzyć faktyczny wykaz towarów i usług tej rejestracji w eSearch plus —
      z listy wyników widać same numery klas, nie ich zakres.
      Zmiana nazwy na tym etapie (brak publikacji na PyPI, brak użytkowników,
      brak umów) jest nieporównanie tańsza niż po wydaniu

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
