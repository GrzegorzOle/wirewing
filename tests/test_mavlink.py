# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import struct

import pytest

from wirewing.mavlink import (
    CRC_EXTRA,
    MavCmd,
    MavFrame,
    MavlinkParser,
    MavMsgId,
    MavResult,
    crc_x25,
    decode_command_ack,
    encode_command,
    encode_v1,
)

# Ramka przechwycona z rzeczywistego kontrolera: ArduCopter 3.6.12 na Cube,
# HEARTBEAT z sys/comp 1/1. Jest to materiał odniesienia — suma kontrolna
# pochodzi od urządzenia, nie z naszej implementacji, więc test wykrywa błąd
# w CRC albo w CRC_EXTRA, którego test typu "zakoduj i zdekoduj" by przepuścił.
REAL_HEARTBEAT = bytes.fromhex("fe09240101000000000002035104037b8b")


def test_crc_wektor_kontrolny() -> None:
    """MAVLink używa MCRF4XX, nie X.25 — różnica to brak końcowej negacji wyniku."""
    assert crc_x25(b"123456789") == 0x6F91
    assert crc_x25(b"123456789") ^ 0xFFFF == 0x906E  # tyle dałby wariant X.25


def test_prawdziwa_ramka_z_urzadzenia() -> None:
    """Najważniejszy test modułu: zgodność z sumą policzoną przez sam autopilot."""
    frames = list(MavlinkParser().feed(REAL_HEARTBEAT))
    assert len(frames) == 1
    frame = frames[0]
    assert frame.crc_ok is True, "suma kontrolna z urządzenia nie zgadza się z naszą"
    assert frame.msg_id == MavMsgId.HEARTBEAT
    assert frame.version == 1
    assert (frame.sysid, frame.compid) == (1, 1)
    assert frame.seq == 0x24
    assert len(frame.payload) == 9


def test_prawdziwa_ramka_dekoduje_sie_na_sensowne_pola() -> None:
    """Ładunek HEARTBEAT rozkłada się na wartości zgodne ze stanem sprzętu."""
    frame = next(iter(MavlinkParser().feed(REAL_HEARTBEAT)))
    custom_mode, mav_type, autopilot, base_mode, status, version = struct.unpack(
        "<IBBBBB", frame.payload
    )
    assert mav_type == 2  # QUADROTOR
    assert autopilot == 3  # ArduPilotMega
    assert version == 3  # MAVLink v3 w polu wersji wiadomości
    assert not base_mode & 0x80, "bit SAFETY_ARMED — maszyna była rozbrojona"
    assert custom_mode == 0  # STABILIZE
    assert status == 4


def test_kodowanie_i_dekodowanie_w_obie_strony() -> None:
    raw = encode_v1(MavMsgId.HEARTBEAT, seq=7, payload=b"\x01" * 9)
    frame = next(iter(MavlinkParser().feed(raw)))
    assert frame.msg_id == MavMsgId.HEARTBEAT
    assert frame.seq == 7
    assert frame.payload == b"\x01" * 9
    assert frame.crc_ok is True


def test_komenda_uzbrojenia_ma_wlasciwy_ksztalt() -> None:
    """ARM w MAVLinku to COMMAND_LONG z numerem komendy, nie osobny typ wiadomości."""
    raw = encode_command(MavCmd.COMPONENT_ARM_DISARM, (1.0,))
    frame = next(iter(MavlinkParser().feed(raw)))
    assert frame.msg_id == MavMsgId.COMMAND_LONG
    assert frame.crc_ok is True
    params = struct.unpack("<7fHBBB", frame.payload)
    assert params[0] == 1.0  # param1 = uzbrój
    assert params[7] == MavCmd.COMPONENT_ARM_DISARM
    assert params[8:] == (1, 1, 0)  # target_system, target_component, confirmation


def test_command_ack_sie_odczytuje() -> None:
    payload = struct.pack("<HB", MavCmd.COMPONENT_ARM_DISARM, MavResult.ACCEPTED)
    frame = MavFrame(msg_id=MavMsgId.COMMAND_ACK, seq=0, sysid=1, compid=1, payload=payload)
    assert decode_command_ack(frame) == (MavCmd.COMPONENT_ARM_DISARM, MavResult.ACCEPTED)


def test_command_ack_odrzuca_inna_ramke() -> None:
    assert decode_command_ack(MavFrame(msg_id=MavMsgId.HEARTBEAT, seq=0, sysid=1, compid=1)) is None


def test_resynchronizacja_po_smieciach() -> None:
    parser = MavlinkParser()
    frames = list(parser.feed(b"\x00\x11\x22\x33" + REAL_HEARTBEAT))
    assert len(frames) == 1
    assert frames[0].crc_ok is True
    assert parser.resyncs >= 1


def test_dobra_ramka_zaraz_za_uszkodzona() -> None:
    """Uszkodzenie jednej ramki nie może przesłonić następnej, poprawnej."""
    zepsuta = bytearray(REAL_HEARTBEAT)
    zepsuta[-1] ^= 0xFF
    parser = MavlinkParser()
    frames = list(parser.feed(bytes(zepsuta) + REAL_HEARTBEAT))
    assert len(frames) == 1
    assert parser.checksum_errors == 1


def test_ramka_w_kawalkach() -> None:
    parser = MavlinkParser()
    assert list(parser.feed(REAL_HEARTBEAT[:5])) == []
    frames = list(parser.feed(REAL_HEARTBEAT[5:]))
    assert len(frames) == 1
    assert frames[0].crc_ok is True


def test_tryb_strict_podnosi_wyjatek() -> None:
    zepsuta = bytearray(REAL_HEARTBEAT)
    zepsuta[-2] ^= 0xFF
    with pytest.raises(ValueError, match="suma kontrolna"):
        list(MavlinkParser(strict=True).feed(bytes(zepsuta)))


def test_nieznana_wiadomosc_jest_oznaczona_nie_zgadywana() -> None:
    """Bez CRC_EXTRA nie da się sprawdzić sumy — parser mówi o tym wprost."""
    nieznany = 199
    assert nieznany not in CRC_EXTRA
    body = struct.pack("<BBBBB", 2, 1, 1, 1, nieznany) + b"\xaa\xbb"
    raw = bytes([0xFE]) + body + struct.pack("<H", 0x1234)
    parser = MavlinkParser()
    frames = list(parser.feed(raw))
    assert len(frames) == 1
    assert frames[0].crc_ok is None
    assert parser.unknown == 1


def test_nie_da_sie_zakodowac_wiadomosci_bez_crc_extra() -> None:
    with pytest.raises(KeyError, match="CRC_EXTRA"):
        encode_v1(199, seq=0, payload=b"")


def test_ramka_v2_sie_dekoduje() -> None:
    """Kodujemy tylko v1, ale odbierać musimy też v2 — urządzenie potrafi przełączyć wersję."""
    payload = b"\x00" * 9
    body = struct.pack("<BBBBBBBBB", len(payload), 0, 0, 5, 1, 1, MavMsgId.HEARTBEAT, 0, 0)
    body += payload
    crc = crc_x25(bytes([CRC_EXTRA[MavMsgId.HEARTBEAT]]), crc_x25(body))
    raw = bytes([0xFD]) + body + struct.pack("<H", crc)
    frames = list(MavlinkParser().feed(raw))
    assert len(frames) == 1
    assert frames[0].version == 2
    assert frames[0].msg_id == MavMsgId.HEARTBEAT
    assert frames[0].crc_ok is True


def test_za_dlugi_ladunek_odrzucony() -> None:
    with pytest.raises(ValueError, match="limit"):
        encode_v1(MavMsgId.HEARTBEAT, seq=0, payload=b"\x00" * 256)


def test_za_duzo_parametrow_komendy() -> None:
    with pytest.raises(ValueError, match="7 parametrów"):
        encode_command(MavCmd.NAV_TAKEOFF, tuple(float(i) for i in range(8)))
