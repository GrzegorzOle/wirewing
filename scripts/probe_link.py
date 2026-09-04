#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Rozpoznaj, jakim protokołem mówi urządzenie po drugiej stronie łącza.

Zanim zaczniesz odtwarzać protokół, warto sprawdzić, czy urządzenie nie mówi
MAVLinkiem — robi tak ogromna część kontrolerów lotu i wtedy cała analiza jest
zbędną pracą. Patrz docs/protocol.md.

Nasłuch jest **w pełni pasywny**: skrypt nie wysyła na łącze ani jednego bajtu
i nie asertuje DTR/RTS, bo część płytek resetuje się przy samym otwarciu portu.

    python scripts/probe_link.py --list          # porty wraz z VID:PID
    python scripts/probe_link.py /dev/ttyUSB0    # nasłuch 5 s przy 115200
    python scripts/probe_link.py COM3 --seconds 10
    python scripts/probe_link.py COM3 --scan     # przemieć typowe prędkości

Liczone są wyłącznie ramki **łańcuchujące się** — takie, po których pod
wyliczonym offsetem stoi kolejny znacznik początku. Samo zliczanie bajtów
myli, bo 0xFE trafia się w losowych danych bez przerwy.

Uwaga przy MAVLinku: wykryta wersja mówi o tym, czego urządzenie używa *teraz*,
a nie co potrafi. ArduPilot dopasowuje wersję protokołu do stacji naziemnej
na danym kanale, więc ten sam kontroler potrafi nadawać v1, dopóki nie
podłączy się do niego stacja mówiąca v2. Rozróżnienie v1/v2 traktuj jako
wskazówkę, nie jako trwałą cechę urządzenia.
"""

from __future__ import annotations

import argparse
import sys
import time

from wirewing.protocol import FrameParser

# Prędkości, od których warto zacząć — uszeregowane wg tego, jak często
# spotyka się je w telemetrii UAV.
COMMON_BAUDS = (115200, 57600, 921600, 38400, 9600)

MAVLINK_V1 = 0xFE
MAVLINK_V2 = 0xFD
MAVLINK_V1_OVERHEAD = 8  # STX, LEN, SEQ, SYSID, COMPID, MSGID + CRC(2)
MAVLINK_V2_OVERHEAD = 12  # STX, LEN, flagi(2), SEQ, SYSID, COMPID, MSGID(3) + CRC(2)

# Producenci, których VID najczęściej widuje się przy kontrolerach lotu.
VENDORS = {
    0x26AC: "3D Robotics / ArduPilot (rodzina PX4 FMU)",
    0x2DAE: "CubePilot / Hex Technology",
    0x1209: "pid.codes (VID współdzielony)",
    0x0483: "STMicroelectronics",
    0x10C4: "Silicon Labs (przejściówka CP210x)",
    0x0403: "FTDI (przejściówka)",
    0x1A86: "QinHeng (przejściówka CH340)",
}


def list_ports() -> int:
    """Wypisz porty szeregowe wraz z identyfikacją sprzętu po USB."""
    try:
        from serial.tools import list_ports as tools  # noqa: PLC0415 - pyserial jest opcjonalny
    except ImportError:
        print("pyserial nie jest zainstalowany: pip install 'wirewing[serial]'", file=sys.stderr)
        return 2

    found = list(tools.comports())
    if not found:
        print("nie znaleziono żadnego portu szeregowego")
        return 1

    for port in found:
        print(f"{port.device}\t{port.description}")
        if port.vid is not None:
            vendor = VENDORS.get(port.vid, port.manufacturer or "nieznany")
            print(f"\tVID:PID {port.vid:04X}:{port.pid:04X}  {vendor}")
    return 0


def listen(port: str, baud: int, seconds: float) -> bytes:
    """Zbieraj bajty przez zadany czas. Nic nie wysyła i nie rusza DTR/RTS."""
    try:
        import serial  # noqa: PLC0415 - pyserial jest opcjonalny
    except ImportError:
        print("pyserial nie jest zainstalowany: pip install 'wirewing[serial]'", file=sys.stderr)
        raise SystemExit(2) from None

    handle = serial.Serial()
    handle.port = port
    handle.baudrate = baud
    handle.timeout = 0.2
    handle.rtscts = False
    handle.dsrdtr = False
    # Nie asertuj linii sterujących — na części płytek otwarcie portu
    # z aktywnym DTR wywołuje reset procesora.
    handle.dtr = False
    handle.rts = False

    handle.open()
    try:
        handle.reset_input_buffer()  # odrzuć zaległości nazbierane w buforze sterownika
        buffer = bytearray()
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            buffer.extend(handle.read(4096))
        return bytes(buffer)
    finally:
        handle.close()


def _chain_from(data: bytes, start: int, sof: int, overhead: int) -> tuple[int, int]:
    """Policz ramki łańcuchujące się od pozycji ``start``. Zwraca (ile, gdzie koniec)."""
    count = 0
    index = start
    while index + 2 <= len(data) and data[index] == sof:
        total = overhead + data[index + 1]
        if index + total > len(data):
            break
        index += total
        count += 1
    return count, index


def count_mavlink(data: bytes, sof: int, overhead: int) -> int:
    """Policz ramki MAVLink, które układają się w ciąg co najmniej dwóch z rzędu."""
    frames = 0
    index = 0
    while index < len(data):
        if data[index] != sof:
            index += 1
            continue
        found, end = _chain_from(data, index, sof, overhead)
        if found >= 2:
            frames += found
            index = end
        else:
            index += 1
    return frames


def count_wirewing(data: bytes) -> int:
    """Policz ramki wirewing z poprawną sumą kontrolną, używając parsera biblioteki."""
    return sum(1 for _ in FrameParser().feed(data))


def probe(port: str, baud: int, seconds: float) -> tuple[int, dict[str, int]]:
    """Nasłuchaj i policz ramki każdego ze znanych protokołów."""
    data = listen(port, baud, seconds)
    counts = {
        "MAVLink v1": count_mavlink(data, MAVLINK_V1, MAVLINK_V1_OVERHEAD),
        "MAVLink v2": count_mavlink(data, MAVLINK_V2, MAVLINK_V2_OVERHEAD),
        "wirewing": count_wirewing(data),
    }
    return len(data), counts


def verdict(counts: dict[str, int]) -> str:
    """Zamień liczby ramek na zdanie, które coś znaczy."""
    best = max(counts, key=lambda name: counts[name])
    if counts[best] == 0:
        return (
            "Nie rozpoznano żadnego znanego protokołu. Jeśli bajty w ogóle płyną, "
            "spróbuj innej prędkości (--scan) albo sprawdź parzystość."
        )
    if best.startswith("MAVLink"):
        return (
            f"To jest {best}. Nie odtwarzaj protokołu ręcznie — zainstaluj osobno "
            "pymavlink (LGPL-3.0, nie jest zależnością wirewing; powody w README)."
        )
    return "To jest protokół wirewing — ramki przechodzą kontrolę CRC."


def report(port: str, baud: int, size: int, counts: dict[str, int]) -> None:
    """Wypisz wynik jednego przebiegu."""
    print(f"\n{port} @ {baud} bit/s — odebrano {size} B")
    if size == 0:
        print("  cisza na łączu: brak danych do analizy")
        return
    for name, found in counts.items():
        print(f"  {name:<12} {found:>5} ramek")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("port", nargs="?", help="port szeregowy, np. /dev/ttyUSB0 albo COM3")
    parser.add_argument("--list", action="store_true", help="wypisz dostępne porty i zakończ")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="prędkość transmisji")
    parser.add_argument("-s", "--seconds", type=float, default=5.0, help="czas nasłuchu")
    parser.add_argument("--scan", action="store_true", help="przemieć typowe prędkości")
    args = parser.parse_args()

    if args.list:
        return list_ports()
    if not args.port:
        parser.error("podaj port albo użyj --list")

    bauds = COMMON_BAUDS if args.scan else (args.baud,)
    for baud in bauds:
        size, counts = probe(args.port, baud, args.seconds)
        report(args.port, baud, size, counts)
        if any(counts.values()):
            print(f"\n{verdict(counts)}")
            return 0

    print("\nNic nie rozpoznano na żadnej z próbowanych prędkości.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
