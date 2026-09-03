# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import pytest

from wirewing import ChecksumError, FrameParser, MsgId, PayloadTooLargeError, crc16_ccitt, encode
from wirewing.protocol import CRC_SIZE, HEADER_SIZE, MAX_PAYLOAD, SOF


def test_crc_wektor_kontrolny() -> None:
    # Kanoniczny wektor CRC-16/CCITT-FALSE.
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_encode_ma_poprawna_dlugosc_i_naglowek() -> None:
    frame = encode(MsgId.ARM, seq=7, payload=b"\x01\x02")
    assert frame.startswith(SOF)
    assert len(frame) == HEADER_SIZE + 2 + CRC_SIZE
    assert frame[3] == MsgId.ARM
    assert frame[4] == 7


def test_roundtrip_pustego_i_pelnego_ladunku() -> None:
    parser = FrameParser()
    for payload in (b"", b"\x00", bytes(range(256)), b"\xff" * MAX_PAYLOAD):
        frames = list(parser.feed(encode(MsgId.TELEMETRY, 1, payload)))
        assert len(frames) == 1
        assert frames[0].payload == payload
        assert frames[0].msg_id == MsgId.TELEMETRY


def test_zbyt_duzy_ladunek_odrzucony() -> None:
    with pytest.raises(PayloadTooLargeError):
        encode(MsgId.TELEMETRY, 0, b"\x00" * (MAX_PAYLOAD + 1))


def test_parser_sklada_ramke_z_pojedynczych_bajtow() -> None:
    parser = FrameParser()
    raw = encode(MsgId.STATUS, 42, b"hello")
    received = [f for byte in raw for f in parser.feed(bytes([byte]))]
    assert len(received) == 1
    assert received[0].payload == b"hello"
    assert received[0].seq == 42


def test_parser_obsluguje_wiele_ramek_w_jednej_paczce() -> None:
    parser = FrameParser()
    blob = b"".join(encode(MsgId.HEARTBEAT, i) for i in range(5))
    frames = list(parser.feed(blob))
    assert [f.seq for f in frames] == [0, 1, 2, 3, 4]


def test_parser_odrzuca_smieci_przed_ramka() -> None:
    parser = FrameParser()
    frames = list(parser.feed(b"\xde\xad\xbe\xef" + encode(MsgId.ACK, 3, b"\x03")))
    assert len(frames) == 1
    assert parser.resyncs >= 1


def test_bledne_crc_jest_pomijane_i_liczone() -> None:
    parser = FrameParser()
    raw = bytearray(encode(MsgId.STATUS, 1, b"abc"))
    raw[-1] ^= 0xFF  # przekłam sumę kontrolną
    assert list(parser.feed(bytes(raw))) == []
    assert parser.checksum_errors == 1


def test_tryb_strict_podnosi_wyjatek() -> None:
    parser = FrameParser(strict=True)
    raw = bytearray(encode(MsgId.STATUS, 1, b"abc"))
    raw[-1] ^= 0xFF
    with pytest.raises(ChecksumError):
        list(parser.feed(bytes(raw)))


def test_parser_wraca_do_synchronizacji_po_uszkodzonej_ramce() -> None:
    parser = FrameParser()
    uszkodzona = bytearray(encode(MsgId.STATUS, 1, b"xyz"))
    uszkodzona[-2] ^= 0xFF
    dobra = encode(MsgId.TELEMETRY, 2, b"ok")
    frames = list(parser.feed(bytes(uszkodzona) + dobra))
    assert len(frames) == 1
    assert frames[0].payload == b"ok"


def test_bufor_nie_rosnie_bez_konca_przy_samych_smieciach() -> None:
    parser = FrameParser()
    for _ in range(100):
        assert list(parser.feed(b"\x00" * 512)) == []
    assert len(parser._buf) <= 2
