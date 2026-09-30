"""Diagnostics output."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from custom_components.wanas.diagnostics import async_get_config_entry_diagnostics


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
    assert diag["polling"]["read_blocks"]
    assert diag["registers"]
    assert diag["entities"]["sensor.supply_airflow"]["address"] == 0
    assert diag["entities"]["switch.bypass"]["write"] == 39
