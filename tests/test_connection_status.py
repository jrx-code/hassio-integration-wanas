"""Connection-status binary sensor attributes."""

from __future__ import annotations

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_connection_status_exposes_bus_log_attributes(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """After a successful poll the sensor is on and carries bus_log + counters."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "binary_sensor.wanas_rekuperator_connection_status"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["failed_polls_in_a_row"] == 0
    assert state.attributes["last_poll_success"] is not None
    assert state.attributes["bus_log"]
    assert all("op" in entry for entry in state.attributes["bus_log"])
    # No host / address leak in attributes.
    assert "192.0.2.10" not in str(state.attributes)

    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    assert entry is not None
    assert entry.unique_id.endswith("_connection_status")
