# wirewing

**Sterowanie bezzałogowcami przez łącze szeregowe RS-232.**

Biblioteka i narzędzie CLI w Pythonie do rozmawiania z kontrolerem lotu po
porcie szeregowym: ramkowanie z sumą kontrolną, odporny na zakłócenia parser
strumieniowy, potwierdzenia z ponawianiem i wątek odbiorczy, który nie wywraca
się na wyjątku w twoim callbacku.

> [!IMPORTANT]
> **Licencja niekomercyjna.** wirewing jest darmowy dla osób prywatnych,
> badaczy, uczelni, organizacji pozarządowych, służb ratowniczych i instytucji
> publicznych. **Użycie w działalności gospodarczej — również wyłącznie
> wewnętrzne — wymaga licencji komercyjnej.** Warunki i cennik:
> **[COMMERCIAL.md](COMMERCIAL.md)** · kontakt: oleksy@cdest.eu

---

## Instalacja

```bash
pip install "wirewing[serial]"
```

Z repozytorium, do pracy nad kodem:

```bash
git clone https://github.com/OWNER/wirewing.git
cd wirewing
pip install -e ".[dev]"
pytest
```

## Szybki start

```python
from wirewing import Link, MsgId, SerialConfig, SerialTransport

config = SerialConfig("/dev/ttyUSB0", baudrate=115200, parity="N")

with Link(SerialTransport(config)) as link:
    link.subscribe(MsgId.TELEMETRY, lambda frame: print(frame.payload.hex(" ")))

    link.command(MsgId.ARM)  # czeka na ACK, ponawia przy braku
    link.command(MsgId.TAKEOFF)
    ...
    link.command(MsgId.LAND)

    print(link.stats)  # LinkStats(sent=4, recv=4, crc_err=0, resync=0, timeouts=0)
```

Bez sprzętu pod ręką użyj `LoopbackTransport` — cały stos działa w pamięci
i nadaje się do testów jednostkowych.

## Wiersz poleceń

```bash
wirewing ports                          # wypisz dostępne porty
wirewing -p /dev/ttyUSB0 status         # odpytaj o stan
wirewing -p /dev/ttyUSB0 monitor -t 30  # podglądaj ruch przez 30 s
wirewing -p /dev/ttyUSB0 send arm       # wyślij komendę i poczekaj na ACK
```

## Stan projektu

| Warstwa | Stan |
|---|---|
| Transport szeregowy (`pyserial`) | gotowe |
| Ramkowanie + CRC-16/CCITT | gotowe |
| Parser strumieniowy z resynchronizacją | gotowe |
| ACK/NAK, ponawianie, heartbeat | gotowe |
| **Mapa rzeczywistych ID wiadomości urządzenia** | **do uzupełnienia** |
| Dekodowanie ładunku telemetrii | do zrobienia |
| GUI / stacja naziemna | poza zakresem tego repozytorium |

> [!WARNING]
> Stałe w `MsgId` oraz układ nagłówka w `protocol.py` są **referencyjne**, a nie
> odtworzone z konkretnego urządzenia. Zanim uruchomisz to na prawdziwym sprzęcie,
> zastąp je wartościami ustalonymi z analizy ruchu — patrz [docs/protocol.md](docs/protocol.md).

## Bezpieczeństwo

To oprogramowanie steruje maszyną, która lata. Nie jest projektowane ani
certyfikowane do zastosowań krytycznych dla bezpieczeństwa (brak zgodności
z DO-178C i normami równoważnymi). Testuj wyłącznie ze zdjętymi śmigłami,
na uwięzi lub w izolowanej przestrzeni. Odpowiedzialność za zgodność z
przepisami EASA/ULC, ubezpieczenie i kwalifikacje pilota spoczywa na operatorze.

Zgłaszanie podatności: [SECURITY.md](SECURITY.md).

## Współpraca

Zgłoszenia błędów i pull requesty są mile widziane. Kod przyjmuję po
podpisaniu [CLA](CLA.md) — wyjaśnienie dlaczego znajdziesz w
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licencja

[PolyForm Noncommercial 1.0.0](LICENSE.md) · SPDX: `PolyForm-Noncommercial-1.0.0`

To nie jest licencja zatwierdzona przez OSI i nie jest to przeoczenie —
[COMMERCIAL.md](COMMERCIAL.md) wyjaśnia, dlaczego tak, i co dostajesz kupując
licencję komercyjną.

wirewing nie jest powiązany z żadnym producentem dronów ani przez niego
wspierany. Nazwy produktów wymienione w dokumentacji są znakami towarowymi
ich właścicieli — patrz [TRADEMARKS.md](TRADEMARKS.md).
