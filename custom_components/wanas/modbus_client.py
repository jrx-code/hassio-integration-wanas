"""Shared Modbus client helpers for the Wanas integration."""

from __future__ import annotations

import logging

from pymodbus.client import AsyncModbusTcpClient, AsyncModbusUdpClient
from pymodbus.framer import FramerType

from .const import PROTOCOL_TCP, PROTOCOL_UDP

_LOGGER = logging.getLogger(__name__)

ModbusClient = AsyncModbusTcpClient | AsyncModbusUdpClient


def create_client(host: str, port: int, protocol: str) -> ModbusClient:
    """Create a Modbus client for the selected protocol."""
    if protocol == PROTOCOL_UDP:
        return AsyncModbusUdpClient(
            host=host, port=port, framer=FramerType.SOCKET
        )
    if protocol == PROTOCOL_TCP:
        return AsyncModbusTcpClient(
            host=host, port=port, framer=FramerType.SOCKET
        )
    # RTU over TCP (default)
    return AsyncModbusTcpClient(host=host, port=port, framer=FramerType.RTU)


async def async_test_connection(
    host: str, port: int, slave_id: int, protocol: str
) -> bool:
    """Return True if holding register 0 can be read."""
    client = create_client(host, port, protocol)
    try:
        await client.connect()
        if not client.connected:
            return False
        result = await client.read_holding_registers(
            address=0, count=1, device_id=slave_id
        )
        return not result.isError()
    except Exception:
        _LOGGER.exception("Error testing Modbus connection to %s:%s", host, port)
        return False
    finally:
        client.close()
