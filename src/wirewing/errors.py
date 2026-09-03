# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""Hierarchia wyjątków wirewing.

Wszystko, co biblioteka rzuca celowo, dziedziczy po :class:`WirewingError`,
dzięki czemu integrator może złapać jeden typ i nie martwić się resztą.
"""

from __future__ import annotations

__all__ = [
    "WirewingError",
    "TransportError",
    "PortClosedError",
    "FrameError",
    "ChecksumError",
    "PayloadTooLargeError",
    "ProtocolError",
    "AckTimeoutError",
    "CommandRejectedError",
]


class WirewingError(Exception):
    """Bazowy wyjątek biblioteki."""


# --- warstwa transportowa (fizyczne łącze RS-232) ---------------------------


class TransportError(WirewingError):
    """Błąd portu szeregowego: brak urządzenia, odmowa dostępu, zerwane łącze."""


class PortClosedError(TransportError):
    """Próba odczytu lub zapisu na zamkniętym transporcie."""


# --- warstwa ramkowania -----------------------------------------------------


class FrameError(WirewingError):
    """Ramka jest uszkodzona strukturalnie i nie da się jej zdekodować."""


class ChecksumError(FrameError):
    """Suma kontrolna CRC-16 się nie zgadza."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"CRC mismatch: oczekiwano 0x{expected:04X}, otrzymano 0x{actual:04X}")
        self.expected = expected
        self.actual = actual


class PayloadTooLargeError(FrameError):
    """Ładunek przekracza limit narzucony przez pole długości."""


# --- warstwa protokołu ------------------------------------------------------


class ProtocolError(WirewingError):
    """Zdalna strona zachowała się niezgodnie z protokołem."""


class AckTimeoutError(ProtocolError):
    """Nie doczekano się potwierdzenia w zadanym czasie."""

    def __init__(self, msg_id: int, seq: int, timeout: float) -> None:
        super().__init__(f"brak ACK dla msg_id=0x{msg_id:02X} seq={seq} w ciągu {timeout:.2f} s")
        self.msg_id = msg_id
        self.seq = seq
        self.timeout = timeout


class CommandRejectedError(ProtocolError):
    """Urządzenie odpowiedziało NAK."""

    def __init__(self, msg_id: int, reason: int) -> None:
        super().__init__(f"komenda 0x{msg_id:02X} odrzucona, kod przyczyny={reason}")
        self.msg_id = msg_id
        self.reason = reason
