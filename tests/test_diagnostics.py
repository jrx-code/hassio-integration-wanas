"""Diagnostics output."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.wanas_community.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redacts_the_host(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """The dump carries the register bank but never the address of the unit."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"
    assert "192.0.2.10" not in str(diag["entry"])
    assert diag["connection"]["protocol"] == "rtu_over_tcp"
    assert "read_blocks" not in diag["polling"]
    assert diag["polling"]["bus_log"]
    assert any(entry["op"] == "read" and entry["ok"] for entry in diag["polling"]["bus_log"])
    assert diag["registers"]
    assert diag["entities"]["sensor.supply_airflow"]["address"] == 0
    assert diag["entities"]["switch.bypass"]["write"] == 39


async def test_diagnostics_bus_log_records_failed_read(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """A rejected read shows up in bus_log with ok=False and an error text."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    err = MagicMock()
    err.isError.return_value = True
    err.__str__ = lambda self: "Modbus IO error"  # noqa: ARG005
    mock_client.read_holding_registers = AsyncMock(return_value=err)

    async with coordinator._bus:
        try:
            await coordinator._read_locked(0, 1)
        except HomeAssistantError:
            pass

    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    failed = [e for e in diag["polling"]["bus_log"] if not e["ok"]]
    assert failed
    assert failed[-1]["op"] == "read"
    assert failed[-1]["address"] == 0
    assert "error" in failed[-1]
