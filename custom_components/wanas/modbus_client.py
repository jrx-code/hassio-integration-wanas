"""Shared Modbus client helpers for the Wanas integration."""

from __future__ import annotations

import logging

from pymodbus.client import AsyncModbusTcpClient, AsyncModbusUdpClient
from pymodbus.framer import FramerType

from .const import PROTOCOL_TCP, PROTOCOL_UDP

_LOGGER = logging.getLogger(__name__)


def create_client(
    host: str, port: int, protocol: str
) -> AsyncModbusTcpClient | AsyncModbusUdpClient:
    """Create a Modbus client based on protocol selection."""
    if protocol == PROTOCOL_UDP:
        return AsyncModbusUdpClient(
            host=host, port=port, framer=FramerType.SOCKET
        )
    if protocol == PROTOCOL_TCP:
        return AsyncModbusTcpClient(
            host=host, port=port, framer=FramerType.SOCKET
        )
    # RTU over TCP
    return AsyncModbusTcpClient(
        host=host, port=port, framer=FramerType.RTU
    )


async def async_test_connection(
    host: str, port: int, slave_id: int, protocol: str
) -> str | None:
    """Test Modbus connection. Returns error key or None on success."""
    client = create_client(host, port, protocol)
    try:
        connected = await client.connect()
        if not connected:
            return "cannot_connect"
        result = await client.read_holding_registers(
            address=0, count=1, device_id=slave_id
        )
        if result.isError():
            return "cannot_connect"
    except Exception:
        _LOGGER.exception("Error testing Modbus connection")
        return "cannot_connect"
    finally:
        client.close()
    return None
