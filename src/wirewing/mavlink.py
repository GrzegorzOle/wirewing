# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""Koder i dekoder MAVLink — natywny, bez zależności zewnętrznych.

Ogromna część kontrolerów lotu mówi MAVLinkiem, więc odtwarzanie dla nich
własnego protokołu jest zbędną pracą. Ten moduł pozwala rozmawiać z takim
urządzeniem, zachowując resztę biblioteki bez zmian: transport, wątek odbiorczy
i publiczne API pozostają te same, wymienia się wyłącznie warstwa ramkowania.

Implementacja jest własna i celowo nie korzysta z ``pymavlink``, który jest na
LGPL-3.0 — wszystkie zależności wirewing pozostają permisywne. Definicje samego
protokołu MAVLink są na licencji MIT, więc odtworzenie ich tutaj jest w porządku.

Zakres
------
Dekodowane są ramki **v1 i v2**, kodowane wyłącznie **v1**. Nie jest to
ograniczenie techniczne, tylko świadomy wybór: ArduPilot przyjmuje v1 zawsze,
a wersja odpowiedzi dopasowuje się do tego, czym mówi stacja naziemna.
Podpisywanie ramek (MAVLink 2 signing) nie jest obsługiwane — ramki podpisane
zostaną rozpoznane i pominięte, a nie błędnie zdekodowane.

Układ ramki v1::

    +-----+-----+-----+-------+--------+-------+---------+-------+
    | STX | LEN | SEQ | SYSID | COMPID | MSGID | PAYLOAD | CRC16 |
    | FE  |     |     |       |        |       |  0..255 | lo hi |
    +-----+-----+-----+-------+--------+-------+---------+-------+
          |<-------------- obszar liczenia CRC ---------->|

Suma kontrolna to CRC-16/X.25 liczone od bajtu ``LEN`` do końca ładunku,
a następnie **dosypywany jest bajt ``CRC_EXTRA``** — inny dla każdego typu
wiadomości. To on chroni przed zdekodowaniem ramki według niezgodnej definicji
i dlatego nie da się obsłużyć wiadomości, której nie ma w tablicy niżej.
"""

from __future__ import annotations

import enum
import struct
from collections.abc import Iterator
from dataclasses import dataclass, field

__all__ = [
    "MAV_STX_V1",
    "MAV_STX_V2",
    "MavMsgId",
    "MavCmd",
    "MavResult",
    "CRC_EXTRA",
    "MavFrame",
    "crc_x25",
    "encode_v1",
    "encode_command",
    "decode_command_ack",
    "MavlinkParser",
]

MAV_STX_V1 = 0xFE
MAV_STX_V2 = 0xFD

_V1_OVERHEAD = 8  # STX, LEN, SEQ, SYSID, COMPID, MSGID + CRC(2)
_V2_OVERHEAD = 12  # STX, LEN, flagi(2), SEQ, SYSID, COMPID, MSGID(3) + CRC(2)
_V2_SIGNATURE = 13  # dokładany, gdy INCOMPAT_FLAGS ma bit 0x01
_V2_INCOMPAT_SIGNED = 0x01

MAX_PAYLOAD = 255


class MavMsgId(enum.IntEnum):
    """Identyfikatory wiadomości MAVLink, których używa ten moduł."""

    HEARTBEAT = 0
    SYS_STATUS = 1
    SYSTEM_TIME = 2
    PARAM_REQUEST_READ = 20
    PARAM_VALUE = 22
    PARAM_SET = 23
    GPS_RAW_INT = 24
    ATTITUDE = 30
    GLOBAL_POSITION_INT = 33
    RC_CHANNELS_RAW = 35
    SERVO_OUTPUT_RAW = 36
    MISSION_CURRENT = 42
    REQUEST_DATA_STREAM = 66
    VFR_HUD = 74
    COMMAND_LONG = 76
    COMMAND_ACK = 77
    POWER_STATUS = 125
    BATTERY_STATUS = 147
    STATUSTEXT = 253


class MavCmd(enum.IntEnum):
    """Komendy przenoszone w ``COMMAND_LONG``.

    W MAVLinku uzbrojenie czy start **nie są typami wiadomości** — to wartości
    pola ``command`` wewnątrz jednej wspólnej wiadomości. Na tym polega główna
    różnica wobec protokołu wirewing, gdzie każda komenda ma własny ``MsgId``.
    """

    NAV_RETURN_TO_LAUNCH = 20
    NAV_LAND = 21
    NAV_TAKEOFF = 22
    DO_MOTOR_TEST = 209
    PREFLIGHT_REBOOT_SHUTDOWN = 246
    COMPONENT_ARM_DISARM = 400


class MavResult(enum.IntEnum):
    """Kody odpowiedzi w ``COMMAND_ACK``."""

    ACCEPTED = 0
    TEMPORARILY_REJECTED = 1
    DENIED = 2
    UNSUPPORTED = 3
    FAILED = 4
    IN_PROGRESS = 5


# Bajt dosypywany do sumy kontrolnej, osobny dla każdego typu wiadomości.
# Pochodzi z definicji protokołu (MIT). Wiadomości spoza tej tablicy nie da się
# zweryfikować — parser oznacza je jako niesprawdzone zamiast zgadywać.
CRC_EXTRA: dict[int, int] = {
    MavMsgId.HEARTBEAT: 50,
    MavMsgId.SYS_STATUS: 124,
    MavMsgId.SYSTEM_TIME: 137,
    MavMsgId.PARAM_REQUEST_READ: 214,
    MavMsgId.PARAM_VALUE: 220,
    MavMsgId.PARAM_SET: 168,
    MavMsgId.GPS_RAW_INT: 24,
    MavMsgId.ATTITUDE: 39,
    MavMsgId.GLOBAL_POSITION_INT: 104,
    MavMsgId.RC_CHANNELS_RAW: 244,
    MavMsgId.SERVO_OUTPUT_RAW: 222,
    MavMsgId.MISSION_CURRENT: 28,
    MavMsgId.REQUEST_DATA_STREAM: 148,
    MavMsgId.VFR_HUD: 20,
    MavMsgId.COMMAND_LONG: 152,
    MavMsgId.COMMAND_ACK: 143,
    MavMsgId.POWER_STATUS: 203,
    MavMsgId.BATTERY_STATUS: 154,
    MavMsgId.STATUSTEXT: 83,
}

_COMMAND_LONG = struct.Struct("<7fHBBB")
_COMMAND_ACK = struct.Struct("<HB")


@dataclass(frozen=True, slots=True)
class MavFrame:
    """Pojedyncza zdekodowana ramka MAVLink."""

    msg_id: int
    seq: int
    sysid: int
    compid: int
    payload: bytes = b""
    version: int = 1
    crc_ok: bool | None = None
    """``None``, gdy typu wiadomości nie ma w :data:`CRC_EXTRA` i nie dało się sprawdzić."""

    def __repr__(self) -> str:  # pragma: no cover - tylko diagnostyka
        try:
            name = MavMsgId(self.msg_id).name
        except ValueError:
            name = f"msg{self.msg_id}"
        return f"MavFrame(v{self.version}, {name}, sys={self.sysid}, len={len(self.payload)})"


def crc_x25(data: bytes, crc: int = 0xFFFF) -> int:
    """Suma kontrolna MAVLinka.

    Dokumentacja MAVLinka nazywa ten wariant „X.25" i pod tą nazwą jest
    powszechnie znany, ale ściśle rzecz biorąc to **CRC-16/MCRF4XX**: ten sam
    wielomian i inicjalizacja co X.25, lecz **bez końcowej negacji wyniku**.
    Pomylenie tych dwóch wariantów daje sumy różniące się o ``0xFFFF`` i jest
    najczęstszym błędem przy pisaniu własnego kodera od zera.

    Kontrolnie: ``crc_x25(b"123456789") == 0x6F91``. Gdyby wyszło ``0x906E``,
    znaczy że w implementacji została końcowa negacja z X.25.
    """
    for byte in data:
        tmp = (byte ^ (crc & 0xFF)) & 0xFF
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    return crc


def _frame_crc(body: bytes, msg_id: int) -> int:
    """Suma kontrolna ramki: CRC po treści, a na końcu bajt CRC_EXTRA."""
    return crc_x25(bytes([CRC_EXTRA[msg_id]]), crc_x25(body))


def encode_v1(
    msg_id: int, seq: int, payload: bytes, *, sysid: int = 255, compid: int = 190
) -> bytes:
    """Złóż ramkę MAVLink v1 gotową do wysłania.

    Domyślne ``sysid=255`` i ``compid=190`` to wartości zwyczajowo przyjęte dla
    stacji naziemnej — urządzenie po nich rozpoznaje, z kim rozmawia.
    """
    if msg_id not in CRC_EXTRA:
        raise KeyError(f"brak CRC_EXTRA dla wiadomości {msg_id} — nie da się jej zakodować")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"ładunek {len(payload)} B przekracza limit {MAX_PAYLOAD} B")
    body = struct.pack("<BBBBB", len(payload), seq & 0xFF, sysid, compid, msg_id) + payload
    return bytes([MAV_STX_V1]) + body + struct.pack("<H", _frame_crc(body, msg_id))


def encode_command(
    command: int,
    params: tuple[float, ...] = (),
    *,
    seq: int = 0,
    target_system: int = 1,
    target_component: int = 1,
    confirmation: int = 0,
    sysid: int = 255,
    compid: int = 190,
) -> bytes:
    """Złóż ``COMMAND_LONG`` — tak w MAVLinku wyraża się komendę.

    Brakujące parametry są dopełniane zerami; komenda ma ich zawsze siedem.
    """
    if len(params) > 7:
        raise ValueError("COMMAND_LONG przyjmuje najwyżej 7 parametrów")
    filled = (*params, *([0.0] * (7 - len(params))))
    payload = _COMMAND_LONG.pack(*filled, command, target_system, target_component, confirmation)
    return encode_v1(MavMsgId.COMMAND_LONG, seq, payload, sysid=sysid, compid=compid)


def decode_command_ack(frame: MavFrame) -> tuple[int, int] | None:
    """Wyłuskaj ``(command, result)`` z ``COMMAND_ACK``. ``None``, gdy to nie ta ramka."""
    if frame.msg_id != MavMsgId.COMMAND_ACK or len(frame.payload) < _COMMAND_ACK.size:
        return None
    command, result = _COMMAND_ACK.unpack_from(frame.payload, 0)
    return int(command), int(result)


@dataclass
class MavlinkParser:
    """Parser strumieniowy MAVLink, odporny na śmieci i gubienie bajtów.

    Zachowuje się jak :class:`wirewing.protocol.FrameParser`: karmisz go dowolnymi
    fragmentami odebranymi z portu, a on oddaje kompletne ramki. Po błędzie sumy
    kontrolnej przesuwa się o jeden bajt i szuka kolejnego znacznika początku.
    """

    strict: bool = False
    """Gdy ``True``, błędna suma kontrolna podnosi wyjątek zamiast być pominięta."""

    _buf: bytearray = field(default_factory=bytearray, repr=False)
    checksum_errors: int = 0
    resyncs: int = 0
    unknown: int = 0
    """Ramki o nieznanym typie — poprawne strukturalnie, ale niesprawdzone."""

    def reset(self) -> None:
        self._buf.clear()

    def feed(self, data: bytes) -> Iterator[MavFrame]:
        """Dołóż odebrane bajty i wygeneruj wszystkie kompletne ramki."""
        self._buf.extend(data)
        while True:
            frame = self._try_pop()
            if frame is None:
                return
            yield frame

    def _find_start(self) -> int | None:
        """Przesuń bufor do najbliższego znacznika początku. ``None``, gdy go nie ma."""
        buf = self._buf
        for index, byte in enumerate(buf):
            if byte in (MAV_STX_V1, MAV_STX_V2):
                if index:
                    del buf[:index]
                    self.resyncs += 1
                return buf[0]
        # Żadnego znacznika — bufor jest w całości śmieciem.
        if buf:
            buf.clear()
            self.resyncs += 1
        return None

    def _try_pop(self) -> MavFrame | None:
        """Wyjmij jedną ramkę albo zwróć ``None``, gdy brakuje danych.

        Pętla jest tutaj, a nie w :meth:`feed`, z tego samego powodu co
        w parserze protokołu wirewing: odrzucenie uszkodzonej ramki musi
        natychmiast prowadzić do kolejnej próby na tym samym buforze.
        """
        while True:
            stx = self._find_start()
            if stx is None or len(self._buf) < 2:
                return None
            layout = self._layout(stx)
            if layout is None:
                return None
            total, header_len, msg_id = layout
            if len(self._buf) < total:
                return None
            frame = self._build(stx, total, header_len, msg_id)
            if frame is not None:
                return frame

    def _layout(self, stx: int) -> tuple[int, int, int] | None:
        """Zwróć ``(długość całkowita, długość nagłówka, msg_id)`` albo ``None``."""
        buf = self._buf
        length = buf[1]
        if stx == MAV_STX_V1:
            if len(buf) < 6:
                return None
            return _V1_OVERHEAD + length, 6, buf[5]
        if len(buf) < 10:
            return None
        extra = _V2_SIGNATURE if buf[2] & _V2_INCOMPAT_SIGNED else 0
        msg_id = buf[7] | (buf[8] << 8) | (buf[9] << 16)
        return _V2_OVERHEAD + length + extra, 10, msg_id

    def _build(self, stx: int, total: int, header_len: int, msg_id: int) -> MavFrame | None:
        """Zbuduj ramkę po weryfikacji sumy. ``None`` oznacza odrzucenie i resynchronizację."""
        buf = self._buf
        length = buf[1]
        payload = bytes(buf[header_len : header_len + length])
        (received,) = struct.unpack_from("<H", buf, header_len + length)

        crc_ok: bool | None = None
        if msg_id in CRC_EXTRA:
            crc_ok = received == _frame_crc(bytes(buf[1 : header_len + length]), msg_id)
            if not crc_ok:
                self.checksum_errors += 1
                del buf[:1]
                self.resyncs += 1
                if self.strict:
                    raise ValueError(f"błędna suma kontrolna ramki {msg_id}")
                return None
        else:
            self.unknown += 1

        version = 1 if stx == MAV_STX_V1 else 2
        sysid, compid = (buf[3], buf[4]) if version == 1 else (buf[5], buf[6])
        seq = buf[2] if version == 1 else buf[4]
        del buf[:total]
        return MavFrame(
            msg_id=msg_id,
            seq=seq,
            sysid=sysid,
            compid=compid,
            payload=payload,
            version=version,
            crc_ok=crc_ok,
        )
