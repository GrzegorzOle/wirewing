# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 Grzegorz Oleksy
"""wirewing — sterowanie bezzałogowcami przez łącze szeregowe RS-232.

Licencja: PolyForm Noncommercial 1.0.0. Użycie komercyjne wymaga odrębnej
licencji — patrz COMMERCIAL.md.
"""

from __future__ import annotations

from .errors import (
    AckTimeoutError,
    ChecksumError,
    CommandRejectedError,
    FrameError,
    PayloadTooLargeError,
    PortClosedError,
    ProtocolError,
    TransportError,
    WirewingError,
)
from .link import Link, LinkStats
from .protocol import Frame, FrameParser, MsgId, NakReason, crc16_ccitt, encode
from .transport import LoopbackTransport, SerialConfig, SerialTransport, Transport

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # protokół
    "Frame",
    "FrameParser",
    "MsgId",
    "NakReason",
    "crc16_ccitt",
    "encode",
    # transport
    "Transport",
    "SerialConfig",
    "SerialTransport",
    "LoopbackTransport",
    # łącze
    "Link",
    "LinkStats",
    # błędy
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
