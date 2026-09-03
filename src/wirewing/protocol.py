# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""Ramkowanie i kodowanie wiadomości.

UWAGA DLA IMPLEMENTUJĄCEGO
--------------------------
Format ramki poniżej jest **referencyjny**, nie odtworzony z konkretnego
urządzenia. Zastąp stałe w :class:`MsgId` oraz układ nagłówka rzeczywistymi
wartościami, które ustalisz analizując ruch na łączu. Reszta biblioteki
(transport, pętla odbiorcza, dopasowywanie ACK) jest od tego niezależna i
nie wymaga zmian.

Układ ramki::

    +--------+--------+--------+--------+--------+--------+---------+--------+
    | SOF_HI | SOF_LO |  VER   | MSG_ID |  SEQ   |     LEN (u16)    | PAYLOAD|
    +--------+--------+--------+--------+--------+--------+---------+--------+
    |  0xA5  |  0x5A  |  0x01  |  ....  |  ....  |   little-endian  |  0..N  |
    +--------+--------+--------+--------+--------+--------+---------+--------+
                                                                    | CRC16 |
                                                                    +--------+

CRC-16/CCITT-FALSE (wielomian 0x1021, init 0xFFFF) liczone od bajtu ``VER``
do końca ``PAYLOAD`` włącznie, zapisywane little-endian.
"""

from __future__ import annotations

import enum
import struct
from collections.abc import Iterator
from dataclasses import dataclass, field

from .errors import ChecksumError, PayloadTooLargeError

__all__ = [
    "SOF",
    "PROTOCOL_VERSION",
    "HEADER_SIZE",
    "CRC_SIZE",
    "MAX_PAYLOAD",
    "MsgId",
    "NakReason",
    "Frame",
    "crc16_ccitt",
    "encode",
    "FrameParser",
]

SOF = b"\xa5\x5a"
PROTOCOL_VERSION = 0x01
HEADER_SIZE = 7  # SOF(2) + VER(1) + MSG_ID(1) + SEQ(1) + LEN(2)
CRC_SIZE = 2
MAX_PAYLOAD = 1024

_HEADER = struct.Struct("<2sBBBH")


class MsgId(enum.IntEnum):
    """Identyfikatory wiadomości.

    Wartości są zastępcze — podmień je na rzeczywiste ID urządzenia.
    """

    HEARTBEAT = 0x01
    ACK = 0x02
    NAK = 0x03
    GET_STATUS = 0x10
    STATUS = 0x11
    TELEMETRY = 0x12
    ARM = 0x20
    DISARM = 0x21
    TAKEOFF = 0x22
    LAND = 0x23
    RETURN_TO_LAUNCH = 0x24
    SET_ATTITUDE = 0x30
    SET_VELOCITY = 0x31
    EMERGENCY_STOP = 0x7F


class NakReason(enum.IntEnum):
    """Kody odrzucenia komendy zwracane w ładunku NAK."""

    UNKNOWN = 0
    UNSUPPORTED_MSG = 1
    BAD_PAYLOAD = 2
    NOT_ARMED = 3
    ALREADY_ARMED = 4
    BUSY = 5
    SAFETY_INTERLOCK = 6


@dataclass(frozen=True, slots=True)
class Frame:
    """Pojedyncza zdekodowana ramka."""

    msg_id: int
    seq: int
    payload: bytes = b""
    version: int = PROTOCOL_VERSION

    def __repr__(self) -> str:  # pragma: no cover - tylko diagnostyka
        try:
            name = MsgId(self.msg_id).name
        except ValueError:
            name = f"0x{self.msg_id:02X}"
        return f"Frame({name}, seq={self.seq}, len={len(self.payload)})"


# --- CRC --------------------------------------------------------------------


def _build_crc_table() -> tuple[int, ...]:
    table = []
    for byte in range(256):
        crc = byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
        table.append(crc)
    return tuple(table)


_CRC_TABLE = _build_crc_table()


def crc16_ccitt(data: bytes, seed: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE. Kontrolnie: ``crc16_ccitt(b"123456789") == 0x29B1``."""
    crc = seed
    for byte in data:
        crc = ((crc << 8) & 0xFFFF) ^ _CRC_TABLE[((crc >> 8) ^ byte) & 0xFF]
    return crc


# --- koder ------------------------------------------------------------------


def encode(
    msg_id: int, seq: int, payload: bytes = b"", *, version: int = PROTOCOL_VERSION
) -> bytes:
    """Złóż kompletną ramkę gotową do wysłania na łącze."""
    if len(payload) > MAX_PAYLOAD:
        raise PayloadTooLargeError(f"ładunek {len(payload)} B przekracza limit {MAX_PAYLOAD} B")
    header = _HEADER.pack(SOF, version & 0xFF, msg_id & 0xFF, seq & 0xFF, len(payload))
    crc = crc16_ccitt(header[2:] + payload)
    return header + payload + struct.pack("<H", crc)


# --- dekoder strumieniowy ---------------------------------------------------


@dataclass
class FrameParser:
    """Parser strumieniowy odporny na przekłamania i gubienie bajtów.

    Karmisz go dowolnymi fragmentami odebranymi z portu, a on oddaje kompletne
    ramki. Po błędzie CRC lub złym nagłówku przesuwa się o jeden bajt i szuka
    następnego znacznika początku — czyli sam się resynchronizuje.
    """

    strict: bool = False
    """Gdy ``True``, błąd CRC podnosi wyjątek zamiast być cicho pominięty."""

    _buf: bytearray = field(default_factory=bytearray, repr=False)
    checksum_errors: int = 0
    resyncs: int = 0

    def reset(self) -> None:
        self._buf.clear()

    def feed(self, data: bytes) -> Iterator[Frame]:
        """Dołóż odebrane bajty i wygeneruj wszystkie kompletne ramki."""
        self._buf.extend(data)
        while True:
            frame = self._try_pop()
            if frame is None:
                return
            yield frame

    def _try_pop(self) -> Frame | None:
        """Wyjmij jedną kompletną ramkę albo zwróć ``None``, gdy brakuje danych.

        Pętla jest tutaj, a nie w :meth:`feed`, celowo: odrzucenie śmieci lub
        ramki z błędnym CRC musi natychmiast prowadzić do kolejnej próby na tym
        samym buforze. ``None`` oznacza wyłącznie „potrzebuję więcej bajtów" —
        gdyby oznaczało też „pominięto śmieci", dobra ramka leżąca zaraz za
        uszkodzoną zostałaby zauważona dopiero przy następnym wywołaniu.
        """
        buf = self._buf

        while True:
            start = buf.find(SOF)
            if start == -1:
                # Zachowaj ostatni bajt — może być pierwszą połową znacznika.
                if len(buf) > 1:
                    del buf[: len(buf) - 1]
                return None
            if start > 0:
                del buf[:start]
                self.resyncs += 1

            if len(buf) < HEADER_SIZE:
                return None

            _, version, msg_id, seq, length = _HEADER.unpack_from(buf, 0)

            if length > MAX_PAYLOAD:
                del buf[:2]
                self.resyncs += 1
                continue

            total = HEADER_SIZE + length + CRC_SIZE
            if len(buf) < total:
                return None

            payload = bytes(buf[HEADER_SIZE : HEADER_SIZE + length])
            (received_crc,) = struct.unpack_from("<H", buf, HEADER_SIZE + length)
            expected_crc = crc16_ccitt(bytes(buf[2:HEADER_SIZE]) + payload)

            if received_crc != expected_crc:
                self.checksum_errors += 1
                del buf[:2]
                self.resyncs += 1
                if self.strict:
                    raise ChecksumError(expected_crc, received_crc)
                continue

            del buf[:total]
            return Frame(msg_id=msg_id, seq=seq, payload=payload, version=version)
