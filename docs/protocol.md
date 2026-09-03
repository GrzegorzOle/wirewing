# Protokół — specyfikacja i jak ją uzupełnić

## Status

Format ramki opisany niżej jest **referencyjny**. Zaimplementowana warstwa
transportowa, ramkowanie i logika ACK są kompletne i przetestowane, ale
**identyfikatory wiadomości i układ ładunków musisz ustalić dla swojego
urządzenia**. Dopóki tego nie zrobisz, biblioteka rozmawia poprawnie sama
ze sobą i nie rozmawia z niczym innym.

## Warstwa fizyczna

| Parametr | Wartość domyślna | Uwagi |
|---|---|---|
| Prędkość | 115200 bit/s | typowa dla telemetrii UAV; spotyka się też 57600 i 921600 |
| Bity danych | 8 | |
| Parzystość | brak (N) | zła parzystość objawia się jako lawina błędów CRC, nie jako brak łączności |
| Bity stopu | 1 | |
| Sterowanie przepływem | brak | RTS/CTS włączasz flagą `--rtscts` |
| Poziomy | ±3…15 V (RS-232) | **nie podłączaj bezpośrednio do UART 3,3 V** — potrzebny konwerter MAX3232 |

> [!CAUTION]
> RS-232 używa napięć do ±15 V. Podłączenie go wprost do pinu UART kontrolera
> lotu niszczy port. Zawsze przez konwerter poziomów.

## Format ramki

```
 0        1        2        3        4        5        6        7 ...    N   N+1
+--------+--------+--------+--------+--------+--------+--------+-----+--------+--------+
| SOF_HI | SOF_LO |  VER   | MSG_ID |  SEQ   |    LEN (u16 LE) |  PAYLOAD  |  CRC16   |
|  0xA5  |  0x5A  |  0x01  |        |        |  lo     hi      |  0..1024  |  lo  hi  |
+--------+--------+--------+--------+--------+--------+--------+-----+--------+--------+
         |<------------------ obszar liczenia CRC ------------------>|
```

- **SOF** — znacznik początku `A5 5A`. Parser szuka go przy resynchronizacji.
- **VER** — wersja protokołu, obecnie `0x01`.
- **MSG_ID** — identyfikator wiadomości, patrz `MsgId` w `protocol.py`.
- **SEQ** — numer sekwencji 0–255, zawija się. Odpowiedź ACK/NAK niesie go
  w pierwszym bajcie ładunku, po czym `Link` dopasowuje ją do oczekującej komendy.
- **LEN** — długość ładunku, little-endian, maksymalnie 1024.
- **CRC16** — CCITT-FALSE (wielomian `0x1021`, init `0xFFFF`), liczone od `VER`
  do końca `PAYLOAD`, zapisane little-endian.

Narzut ramki: 9 bajtów.

### Wektor kontrolny CRC

`crc16_ccitt(b"123456789") == 0x29B1` — jeśli twoja implementacja po drugiej
stronie łącza daje inny wynik, macie różne warianty CRC-16. Wariantów jest
kilkanaście i różnią się inicjalizacją oraz odbiciem bitów.

### Przykładowa ramka

`ARM` (0x20), seq 7, bez ładunku:

```
A5 5A 01 20 07 00 00 <crc_lo> <crc_hi>
```

## ACK i NAK

| Wiadomość | Ładunek |
|---|---|
| `ACK` (0x02) | `[seq_potwierdzanej_komendy]` |
| `NAK` (0x03) | `[seq_potwierdzanej_komendy, kod_przyczyny]` |

Kody przyczyny w `NakReason`. `Link.command()` zamienia NAK na wyjątek
`CommandRejectedError`, a brak odpowiedzi — po wyczerpaniu ponowień — na
`AckTimeoutError`.

## Jak ustalić rzeczywisty protokół urządzenia

Kolejność, która zwykle najszybciej daje wynik:

1. **Sprawdź, czy to nie jest MAVLink.** Ogromna część kontrolerów lotu mówi
   MAVLink-iem. Znacznik startu `0xFE` (v1) lub `0xFD` (v2) na początku ramek
   oznacza, że nie musisz niczego odtwarzać — użyj `pymavlink` i oszczędź
   sobie tygodni. Sprawdź to **zanim** zaczniesz cokolwiek analizować.

   Najprościej pasywnym nasłuchem — otwórz port **wyłącznie do odczytu**,
   zbierz kilka sekund ruchu i policz wystąpienia znaczników:

   ```python
   import serial

   port = serial.Serial()
   port.port, port.baudrate, port.timeout = "/dev/ttyUSB0", 115200, 0.2
   port.dtr = port.rts = False  # nie asertuj DTR/RTS - część płytek resetuje się przy otwarciu
   port.open()
   data = b"".join(port.read(4096) for _ in range(25))
   port.close()

   for name, sof in (("MAVLink v1", b"\xfe"), ("MAVLink v2", b"\xfd"), ("wirewing", b"\xa5\x5a")):
       print(name, data.count(sof))
   ```

   Przewaga `0xFE`/`0xFD` przy zerze na `A5 5A` przesądza sprawę: zainstaluj
   `wirewing[mavlink]` i nie odtwarzaj niczego ręcznie. O konsekwencjach
   licencyjnych tego extra (LGPL-3.0) mówi README.

   Przy nasłuchu przydaje się też identyfikacja sprzętu po USB —
   `python -m serial.tools.list_ports -v` pokaże VID:PID i producenta, co
   często wskazuje płytę szybciej niż analiza ruchu.
2. **Podsłuchaj oryginalną aplikację.** Wepnij analizator logiczny albo
   przejściówkę w tryb pasywny między aplikacją producenta a urządzeniem
   i zapisz ruch w spoczynku.
3. **Znajdź granice ramek.** Szukaj powtarzalnego prefiksu (2 bajty) oraz
   pola długości. Ramki heartbeat wysyłane cyklicznie są najłatwiejszym
   punktem zaczepienia — powtarzają się identycznie co stały interwał.
4. **Ustal wariant CRC.** Mając kilkanaście poprawnych ramek, przepuść je
   przez [reveng](https://reveng.sourceforge.io/) — narzędzie samo wykryje
   wielomian, inicjalizację i odbicie bitów.
5. **Zmapuj komendy pojedynczo.** Jedna akcja w aplikacji → jedna zmiana
   w zrzucie. Notuj w tabeli poniżej.
6. **Zweryfikuj na ziemi, ze zdjętymi śmigłami.**

### Aspekt prawny

W Unii Europejskiej analiza protokołu w celu osiągnięcia interoperacyjności
jest wprost dozwolona: **dyrektywa 2009/24/WE, art. 6**, a art. 8 unieważnia
postanowienia umowne, które by tego zakazywały. Dwa ograniczenia, o których
trzeba pamiętać:

- uzyskanych informacji **nie wolno użyć do stworzenia programu istotnie
  podobnego** w wyrazie do oryginału;
- nie wolno przeklejać zdekompilowanego kodu.

Dokumentuj proces — data, metoda, kto wykonywał. Przy sporze to jedyne, co
odróżnia dozwoloną analizę interoperacyjności od zarzutu skopiowania.

## Tabela do uzupełnienia

| MSG_ID | Nazwa | Kierunek | Ładunek | Zweryfikowane na |
|---|---|---|---|---|
| | | → / ← | | |

## Dekodowanie telemetrii

Do zrobienia. Docelowo `wirewing.telemetry` z definicjami pól opisanymi
deklaratywnie (`struct`-owe formaty + skalowanie), żeby dodanie nowego
urządzenia nie wymagało pisania parsera od zera.
