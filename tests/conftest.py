"""Fixtures for the Wanas tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_PORT

from custom_components.wanas.const import (
    CONF_HAS_COOLER,
    CONF_HAS_HEATER,
    CONF_HAS_HUMIDIFIER,
    CONF_PROTOCOL,
    CONF_SLAVE_ID,
    DEFAULT_PROTOCOL,
    DOMAIN,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"

CONNECTION = {
    CONF_HOST: "192.0.2.10",
    CONF_PORT: 5503,
    CONF_SLAVE_ID: 1,
    CONF_PROTOCOL: DEFAULT_PROTOCOL,
}
ALL_MODULES = {CONF_HAS_HEATER: True, CONF_HAS_COOLER: True, CONF_HAS_HUMIDIFIER: True}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/wanas in every test."""
    return


def _read_result(count: int, start: int = 0):
    result = MagicMock()
    result.isError.return_value = False
    # Distinct values per address so a misread block shows up as a wrong number.
    result.registers = [start + i for i in range(count)]
    return result


@pytest.fixture
def mock_client():
    """A pymodbus client that always answers."""
    client = MagicMock()
    client.connected = True
    client.connect = AsyncMock(return_value=True)
    client.close = MagicMock()

    async def read(address, count, device_id):  # noqa: ARG001
        return _read_result(count, address)

    async def write(address, value, device_id):  # noqa: ARG001
        ok = MagicMock()
        ok.isError.return_value = False
        return ok

    client.read_holding_registers = AsyncMock(side_effect=read)
    client.write_register = AsyncMock(side_effect=write)

    with patch(
        "custom_components.wanas.coordinator.AsyncModbusTcpClient", return_value=client
    ), patch(
        "custom_components.wanas.config_flow.AsyncModbusTcpClient", return_value=client
    ):
        yield client


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A loaded-shaped entry at the current version."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="192.0.2.10:5503:1",
        title="Wanas (192.0.2.10)",
        data={**CONNECTION, **ALL_MODULES},
    )
