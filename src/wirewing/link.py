# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""Łącze wysokiego poziomu: wątek odbiorczy, numeracja sekwencji, ACK/NAK.

Typowe użycie::

    from wirewing import Link, SerialConfig, SerialTransport

    with Link(SerialTransport(SerialConfig("/dev/ttyUSB0"))) as link:
        link.subscribe(MsgId.TELEMETRY, lambda f: print(f.payload.hex()))
        link.command(MsgId.ARM)
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from types import TracebackType

from .errors import AckTimeoutError, CommandRejectedError, TransportError
from .protocol import Frame, FrameParser, MsgId, encode
from .transport import Transport

__all__ = ["Link", "LinkStats"]

log = logging.getLogger("wirewing.link")

Handler = Callable[[Frame], None]


class LinkStats:
    """Liczniki diagnostyczne — przydatne przy ocenie jakości łącza."""

    __slots__ = ("frames_sent", "frames_received", "checksum_errors", "resyncs", "timeouts")

    def __init__(self) -> None:
        self.frames_sent = 0
        self.frames_received = 0
        self.checksum_errors = 0
        self.resyncs = 0
        self.timeouts = 0

    def __repr__(self) -> str:
        return (
            f"LinkStats(sent={self.frames_sent}, recv={self.frames_received}, "
            f"crc_err={self.checksum_errors}, resync={self.resyncs}, "
            f"timeouts={self.timeouts})"
        )


class Link:
    """Sesja komunikacyjna z urządzeniem.

    Klasa jest bezpieczna wątkowo: wysyłać można z wielu wątków, odbiór
    obsługuje jeden wątek tła, a callbacki wołane są właśnie z niego —
    dlatego powinny być krótkie i nie blokować.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        ack_timeout: float = 1.0,
        retries: int = 2,
        heartbeat_interval: float | None = 1.0,
    ) -> None:
        self.transport = transport
        self.ack_timeout = ack_timeout
        self.retries = retries
        self.heartbeat_interval = heartbeat_interval
        self.stats = LinkStats()

        self._parser = FrameParser()
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._handlers: dict[int, list[Handler]] = defaultdict(list)
        self._pending: dict[int, threading.Event] = {}
        self._responses: dict[int, Frame] = {}
        self._pending_lock = threading.Lock()
        self._stop = threading.Event()
        self._rx_thread: threading.Thread | None = None
        self._hb_thread: threading.Thread | None = None

    # --- cykl życia ---------------------------------------------------------

    def open(self) -> None:
        if not self.transport.is_open:
            self.transport.open()
        self._stop.clear()
        self._rx_thread = threading.Thread(target=self._rx_loop, name="wirewing-rx", daemon=True)
        self._rx_thread.start()
        if self.heartbeat_interval:
            self._hb_thread = threading.Thread(
                target=self._heartbeat_loop, name="wirewing-hb", daemon=True
            )
            self._hb_thread.start()

    def close(self) -> None:
        self._stop.set()
        for thread in (self._rx_thread, self._hb_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)
        self._rx_thread = self._hb_thread = None
        self.transport.close()

    def __enter__(self) -> Link:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- wysyłka ------------------------------------------------------------

    def _next_seq(self) -> int:
        with self._seq_lock:
            self._seq = (self._seq + 1) & 0xFF
            return self._seq

    def send(self, msg_id: int, payload: bytes = b"") -> int:
        """Wyślij ramkę bez czekania na potwierdzenie. Zwraca użyty numer sekwencji."""
        seq = self._next_seq()
        self.transport.write(encode(msg_id, seq, payload))
        self.stats.frames_sent += 1
        return seq

    def command(self, msg_id: int, payload: bytes = b"", *, timeout: float | None = None) -> Frame:
        """Wyślij komendę i poczekaj na ACK, ponawiając przy braku odpowiedzi.

        Rzuca :class:`AckTimeoutError`, jeśli wyczerpią się próby, albo
        :class:`CommandRejectedError`, gdy urządzenie odpowie NAK.
        """
        timeout = self.ack_timeout if timeout is None else timeout
        last_seq = 0

        for attempt in range(self.retries + 1):
            seq = self._next_seq()
            last_seq = seq
            event = threading.Event()
            with self._pending_lock:
                self._pending[seq] = event

            try:
                self.transport.write(encode(msg_id, seq, payload))
                self.stats.frames_sent += 1
                if event.wait(timeout):
                    with self._pending_lock:
                        response = self._responses.pop(seq)
                    if response.msg_id == MsgId.NAK:
                        reason = response.payload[1] if len(response.payload) > 1 else 0
                        raise CommandRejectedError(msg_id, reason)
                    return response
            finally:
                with self._pending_lock:
                    self._pending.pop(seq, None)
                    self._responses.pop(seq, None)

            self.stats.timeouts += 1
            if attempt < self.retries:
                log.warning(
                    "brak ACK dla 0x%02X (próba %d/%d), ponawiam",
                    msg_id,
                    attempt + 1,
                    self.retries + 1,
                )

        raise AckTimeoutError(msg_id, last_seq, timeout)

    # --- odbiór -------------------------------------------------------------

    def subscribe(self, msg_id: int, handler: Handler) -> Callable[[], None]:
        """Zarejestruj callback dla danego typu wiadomości.

        Zwraca funkcję, której wywołanie wypisuje subskrypcję.
        """
        self._handlers[int(msg_id)].append(handler)

        def unsubscribe() -> None:
            with self._pending_lock:
                handlers = self._handlers.get(int(msg_id), [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def _rx_loop(self) -> None:
        while not self._stop.is_set():
            try:
                chunk = self.transport.read()
            except TransportError:
                log.exception("łącze zerwane, kończę pętlę odbiorczą")
                break
            if not chunk:
                time.sleep(0.002)
                continue
            for frame in self._parser.feed(chunk):
                self.stats.frames_received += 1
                self._dispatch(frame)
            self.stats.checksum_errors = self._parser.checksum_errors
            self.stats.resyncs = self._parser.resyncs

    def _dispatch(self, frame: Frame) -> None:
        if frame.msg_id in (MsgId.ACK, MsgId.NAK) and frame.payload:
            acked_seq = frame.payload[0]
            with self._pending_lock:
                event = self._pending.get(acked_seq)
                if event is not None:
                    self._responses[acked_seq] = frame
                    event.set()

        for handler in list(self._handlers.get(frame.msg_id, ())):
            try:
                handler(frame)
            except Exception:  # callback użytkownika nie może ubić wątku RX
                log.exception("handler dla 0x%02X rzucił wyjątek", frame.msg_id)

    def _heartbeat_loop(self) -> None:
        interval = self.heartbeat_interval or 1.0
        while not self._stop.wait(interval):
            try:
                self.send(MsgId.HEARTBEAT)
            except TransportError:
                log.warning("nie udało się wysłać heartbeat")
                break
