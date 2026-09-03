# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""Interfejs wiersza poleceń: ``wirewing <komenda>``."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from . import __version__
from .errors import WirewingError
from .link import Link
from .protocol import MsgId
from .transport import SerialConfig, SerialTransport

LICENSE_BANNER = (
    "wirewing jest udostępniony na licencji PolyForm Noncommercial 1.0.0.\n"
    "Użycie komercyjne wymaga odrębnej licencji — zobacz COMMERCIAL.md."
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wirewing",
        description="Sterowanie bezzałogowcem przez RS-232.",
        epilog=LICENSE_BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"wirewing {__version__}")
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", help="port szeregowy")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="prędkość transmisji")
    parser.add_argument("--parity", default="N", choices=["N", "E", "O"], help="parzystość")
    parser.add_argument("--rtscts", action="store_true", help="sprzętowe sterowanie przepływem")
    parser.add_argument("-v", "--verbose", action="store_true", help="logi diagnostyczne")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ports", help="wypisz dostępne porty szeregowe")

    monitor = sub.add_parser("monitor", help="nasłuchuj i wypisuj ramki")
    monitor.add_argument("-t", "--seconds", type=float, default=0.0, help="0 = bez końca")

    status = sub.add_parser("status", help="odpytaj urządzenie o stan")
    status.add_argument("--timeout", type=float, default=2.0)

    send = sub.add_parser("send", help="wyślij pojedynczą komendę")
    send.add_argument("message", choices=[m.name.lower() for m in MsgId])
    send.add_argument("--payload", default="", help="ładunek w hex, np. 01ff")
    send.add_argument("--no-ack", action="store_true", help="nie czekaj na potwierdzenie")

    return parser


def _list_ports() -> int:
    try:
        from serial.tools import list_ports  # noqa: PLC0415 - pyserial jest opcjonalny
    except ImportError:
        print("pyserial nie jest zainstalowany: pip install 'wirewing[serial]'", file=sys.stderr)
        return 2

    found = list(list_ports.comports())
    if not found:
        print("nie znaleziono żadnego portu szeregowego")
        return 1
    for port in found:
        print(f"{port.device}\t{port.description}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    if args.command == "ports":
        return _list_ports()

    config = SerialConfig(args.port, baudrate=args.baud, parity=args.parity, rtscts=args.rtscts)

    try:
        with Link(SerialTransport(config)) as link:
            if args.command == "monitor":
                link.subscribe(MsgId.TELEMETRY, lambda f: print(f"{f!r} {f.payload.hex(' ')}"))
                link.subscribe(MsgId.STATUS, lambda f: print(f"{f!r} {f.payload.hex(' ')}"))
                deadline = time.monotonic() + args.seconds if args.seconds else None
                try:
                    while deadline is None or time.monotonic() < deadline:
                        time.sleep(0.2)
                except KeyboardInterrupt:
                    pass
                print(link.stats)

            elif args.command == "status":
                frame = link.command(MsgId.GET_STATUS, timeout=args.timeout)
                print(f"{frame!r} {frame.payload.hex(' ')}")

            elif args.command == "send":
                msg = MsgId[args.message.upper()]
                payload = bytes.fromhex(args.payload) if args.payload else b""
                if args.no_ack:
                    seq = link.send(msg, payload)
                    print(f"wysłano {msg.name} seq={seq}")
                else:
                    print(repr(link.command(msg, payload)))

    except WirewingError as exc:
        print(f"błąd: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
