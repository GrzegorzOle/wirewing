# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""Warstwa transportowa — fizyczne łącze RS-232 oraz atrapa do testów.

Reszta biblioteki zna wyłącznie protokół :class:`Transport`, więc podmiana
prawdziwego portu na atrapę (albo na TCP, albo na przechwycony log) nie
wymaga zmian w warstwach wyżej.
"""

from __future__ import annotations

import contextlib
import threading
from collections import deque
from types import TracebackType
from typing import Protocol, runtime_checkable

from .errors import PortClosedError, TransportError

__all__ = ["Transport", "SerialConfig", "SerialTransport", "LoopbackTransport"]


@runtime_checkable
class Transport(Protocol):
    """Minimalny kontrakt łącza bajtowego."""

    @property
    def is_open(self) -> bool: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def read(self, size: int = 4096) -> bytes:
        """Zwróć do ``size`` bajtów. Pusty wynik oznacza timeout, nie koniec łącza."""

    def write(self, data: bytes) -> int: ...


class SerialConfig:
    """Parametry portu szeregowego.

    Domyślne wartości (115200 8N1, bez sterowania przepływem) to najczęstszy
    układ w telemetrii UAV. Zweryfikuj je z dokumentacją swojego urządzenia —
    zły parytet objawia się jako lawina błędów CRC, a nie jako brak łączności.
    """

    __slots__ = (
        "port",
        "baudrate",
        "bytesize",
        "parity",
        "stopbits",
        "timeout",
        "write_timeout",
        "rtscts",
        "dsrdtr",
    )

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 115200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: float = 1,
        timeout: float = 0.1,
        write_timeout: float = 1.0,
        rtscts: bool = False,
        dsrdtr: bool = False,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr

    def __repr__(self) -> str:
        return (
            f"SerialConfig({self.port!r}, {self.baudrate} "
            f"{self.bytesize}{self.parity}{self.stopbits:g})"
        )


class SerialTransport:
    """Port szeregowy oparty o ``pyserial``."""

    def __init__(self, config: SerialConfig) -> None:
        self.config = config
        self._serial: object | None = None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return self._serial is not None and bool(getattr(self._serial, "is_open", False))

    def open(self) -> None:
        if self.is_open:
            return
        try:
            import serial  # noqa: PLC0415 - opóźniony import: pyserial jest opcjonalny
        except ImportError as exc:  # pragma: no cover
            raise TransportError(
                "pyserial nie jest zainstalowany — użyj `pip install wirewing[serial]`"
            ) from exc

        cfg = self.config
        try:
            self._serial = serial.Serial(
                port=cfg.port,
                baudrate=cfg.baudrate,
                bytesize=cfg.bytesize,
                parity=cfg.parity,
                stopbits=cfg.stopbits,
                timeout=cfg.timeout,
                write_timeout=cfg.write_timeout,
                rtscts=cfg.rtscts,
                dsrdtr=cfg.dsrdtr,
            )
        except Exception as exc:  # serial.SerialException i pochodne
            raise TransportError(f"nie udało się otworzyć {cfg.port}: {exc}") from exc

    def close(self) -> None:
        serial_port = self._serial
        self._serial = None
        if serial_port is not None:
            # Zamykanie nie może rzucać — port i tak jest już uznany za zamknięty.
            with contextlib.suppress(Exception):
                serial_port.close()  # type: ignore[attr-defined]

    def read(self, size: int = 4096) -> bytes:
        port = self._require_open()
        try:
            waiting = getattr(port, "in_waiting", 0) or 1
            data = port.read(min(size, max(waiting, 1)))  # type: ignore[attr-defined]
            return bytes(data)
        except Exception as exc:
            raise TransportError(f"błąd odczytu z {self.config.port}: {exc}") from exc

    def write(self, data: bytes) -> int:
        port = self._require_open()
        with self._lock:
            try:
                return int(port.write(data) or 0)  # type: ignore[attr-defined]
            except Exception as exc:
                raise TransportError(f"błąd zapisu do {self.config.port}: {exc}") from exc

    def _require_open(self) -> object:
        if not self.is_open or self._serial is None:
            raise PortClosedError(f"port {self.config.port} nie jest otwarty")
        return self._serial

    def __enter__(self) -> SerialTransport:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class LoopbackTransport:
    """Atrapa łącza trzymana w pamięci — pozwala testować bez sprzętu.

    Wszystko, co zapiszesz, ląduje w :attr:`written`. Bajty, które ma
    „odebrać" aplikacja, wstrzykujesz metodą :meth:`inject`.
    """

    def __init__(self) -> None:
        self.written = bytearray()
        self._inbox: deque[bytes] = deque()
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def inject(self, data: bytes) -> None:
        """Udawaj, że urządzenie przysłało te bajty."""
        self._inbox.append(data)

    def read(self, size: int = 4096) -> bytes:
        if not self._open:
            raise PortClosedError("transport zamknięty")
        if not self._inbox:
            return b""
        chunk = self._inbox.popleft()
        if len(chunk) > size:
            self._inbox.appendleft(chunk[size:])
            return chunk[:size]
        return chunk

    def write(self, data: bytes) -> int:
        if not self._open:
            raise PortClosedError("transport zamknięty")
        self.written.extend(data)
        return len(data)

    def __enter__(self) -> LoopbackTransport:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
