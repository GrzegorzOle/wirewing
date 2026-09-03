# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import threading
import time

import pytest

from wirewing import (
    AckTimeoutError,
    CommandRejectedError,
    Link,
    LoopbackTransport,
    MsgId,
    NakReason,
    PortClosedError,
    encode,
)
from wirewing.protocol import FrameParser


class FakeDevice(LoopbackTransport):
    """Atrapa urządzenia, która automatycznie odpowiada ACK lub NAK."""

    def __init__(self, *, nak_for: set[int] | None = None, silent: bool = False) -> None:
        super().__init__()
        self.nak_for = nak_for or set()
        self.silent = silent
        self._parser = FrameParser()
        self.received: list[int] = []

    def write(self, data: bytes) -> int:
        written = super().write(data)
        for frame in self._parser.feed(data):
            self.received.append(frame.msg_id)
            if self.silent or frame.msg_id == MsgId.HEARTBEAT:
                continue
            if frame.msg_id in self.nak_for:
                self.inject(encode(MsgId.NAK, 0, bytes([frame.seq, NakReason.SAFETY_INTERLOCK])))
            else:
                self.inject(encode(MsgId.ACK, 0, bytes([frame.seq])))
        return written


def test_command_dostaje_ack() -> None:
    with Link(FakeDevice(), heartbeat_interval=None) as link:
        response = link.command(MsgId.ARM)
        assert response.msg_id == MsgId.ACK
        assert link.stats.frames_sent == 1


def test_command_podnosi_wyjatek_przy_nak() -> None:
    device = FakeDevice(nak_for={MsgId.TAKEOFF})
    with Link(device, heartbeat_interval=None) as link:
        with pytest.raises(CommandRejectedError) as exc:
            link.command(MsgId.TAKEOFF)
        assert exc.value.reason == NakReason.SAFETY_INTERLOCK


def test_command_ponawia_i_konczy_timeoutem() -> None:
    device = FakeDevice(silent=True)
    with Link(device, heartbeat_interval=None, ack_timeout=0.05, retries=2) as link:
        with pytest.raises(AckTimeoutError):
            link.command(MsgId.ARM)
        assert len(device.received) == 3  # pierwsza próba + 2 ponowienia
        assert link.stats.timeouts == 3


def test_numery_sekwencji_zawijaja_sie_po_255() -> None:
    with Link(FakeDevice(), heartbeat_interval=None) as link:
        link._seq = 254
        assert link.send(MsgId.HEARTBEAT) == 255
        assert link.send(MsgId.HEARTBEAT) == 0


def test_subskrypcja_i_wypisanie() -> None:
    device = FakeDevice()
    odebrane: list[bytes] = []
    with Link(device, heartbeat_interval=None) as link:
        unsubscribe = link.subscribe(MsgId.TELEMETRY, lambda f: odebrane.append(f.payload))
        device.inject(encode(MsgId.TELEMETRY, 1, b"aaa"))
        _wait_for(lambda: len(odebrane) == 1)

        unsubscribe()
        device.inject(encode(MsgId.TELEMETRY, 2, b"bbb"))
        time.sleep(0.05)

    assert odebrane == [b"aaa"]


def test_wyjatek_w_handlerze_nie_zabija_watku_odbiorczego() -> None:
    device = FakeDevice()
    ok: list[int] = []
    with Link(device, heartbeat_interval=None) as link:
        link.subscribe(MsgId.TELEMETRY, lambda f: (_ for _ in ()).throw(RuntimeError("boom")))
        link.subscribe(MsgId.TELEMETRY, lambda f: ok.append(f.seq))
        device.inject(encode(MsgId.TELEMETRY, 9, b""))
        _wait_for(lambda: ok == [9])
        assert link._rx_thread is not None and link._rx_thread.is_alive()


def test_heartbeat_jest_wysylany_cyklicznie() -> None:
    device = FakeDevice()
    with Link(device, heartbeat_interval=0.02) as link:
        _wait_for(lambda: device.received.count(MsgId.HEARTBEAT) >= 3, timeout=2.0)
        assert link.stats.frames_sent >= 3


def test_zamkniety_transport_odmawia_zapisu() -> None:
    transport = LoopbackTransport()
    with pytest.raises(PortClosedError):
        transport.write(b"x")


def _wait_for(predicate, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("warunek nie spełniony w zadanym czasie")


def test_link_jest_bezpieczny_watkowo_przy_wysylce() -> None:
    device = FakeDevice()
    with Link(device, heartbeat_interval=None) as link:
        threads = [
            threading.Thread(target=lambda: [link.send(MsgId.HEARTBEAT) for _ in range(20)])
            for _ in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert link.stats.frames_sent == 80
