"""Config and options flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.wanas.const import (
    CONF_HAS_COOLER,
    CONF_HAS_HEATER,
    CONF_HAS_HUMIDIFIER,
    CONF_HAS_MAXICONTROL,
    CONF_REGISTERS,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DOMAIN,
)

from .conftest import ALL_MODULES, CONNECTION


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_client) -> None:
    """A working connection produces an entry keyed by host:port:slave."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CONNECTION, **ALL_MODULES, "show_advanced": False}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "192.0.2.10:5503:1"
    assert result["result"].data[CONF_HAS_HEATER] is True
    # Room panels are an add-on: not ticked unless the user says so.
    assert result["result"].data[CONF_HAS_MAXICONTROL] is False


async def test_cannot_connect(hass: HomeAssistant) -> None:
    """A refused connection keeps the form up with an error."""
    client = MagicMock()
    client.connected = False
    client.close = MagicMock()

    async def connect():
        return False

    client.connect = connect
    with patch("custom_components.wanas.config_flow.AsyncModbusTcpClient", return_value=client):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**CONNECTION, **ALL_MODULES, "show_advanced": False}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_aborts_without_touching_the_bus(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """The duplicate check must happen before a second Modbus session is opened."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CONNECTION, **ALL_MODULES, "show_advanced": False}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_client.connect.assert_not_called()


async def test_advanced_step_stores_register_overrides(
    hass: HomeAssistant, mock_client
) -> None:
    """The advanced step writes its overrides into options."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CONNECTION, **ALL_MODULES, "show_advanced": True}
    )
    assert result["step_id"] == "registers"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"sensors": {"supply_airflow_name": "Nawiew", "supply_airflow_address": 0}}
    )
    await hass.async_block_till_done()

    assert result["result"].options[CONF_REGISTERS]["supply_airflow_name"] == "Nawiew"


async def test_options_keep_register_overrides(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Saving the options form must not wipe the advanced configuration."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_REGISTERS: {"supply_airflow_name": "Nawiew"}}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HAS_HEATER: True, CONF_HAS_COOLER: False, CONF_HAS_HUMIDIFIER: True,
         CONF_SCAN_INTERVAL: 45},
    )
    await hass.async_block_till_done()

    assert config_entry.options[CONF_REGISTERS] == {"supply_airflow_name": "Nawiew"}
    assert config_entry.options[CONF_HAS_COOLER] is False
    assert config_entry.options[CONF_SCAN_INTERVAL] == 45


@pytest.mark.parametrize("interval", [0, 4, 601])
async def test_options_reject_silly_intervals(
    hass: HomeAssistant, config_entry, mock_client, interval: int
) -> None:
    """The polling interval is bounded."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    with pytest.raises(Exception):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_HAS_HEATER: True, CONF_HAS_COOLER: True, CONF_HAS_HUMIDIFIER: True,
             CONF_SCAN_INTERVAL: interval},
        )
