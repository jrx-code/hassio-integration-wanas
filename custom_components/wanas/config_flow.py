"""Config flow for Wanas integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient, AsyncModbusUdpClient
from pymodbus.framer import FramerType

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import section

from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    CONF_PROTOCOL,
    CONF_REGISTERS,
    CONF_SHOW_ADVANCED,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DEFAULT_PROTOCOL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    NUMBER_DESCRIPTIONS,
    PROTOCOL_OPTIONS,
    PROTOCOL_TCP,
    PROTOCOL_UDP,
    SENSOR_DESCRIPTIONS,
    SWITCH_DESCRIPTIONS,
    get_default_register_config,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
        vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(PROTOCOL_OPTIONS),
        vol.Optional(CONF_SHOW_ADVANCED, default=False): bool,
    }
)


def _create_client(
    host: str, port: int, protocol: str
) -> AsyncModbusTcpClient | AsyncModbusUdpClient:
    """Create a Modbus client based on protocol selection."""
    if protocol == PROTOCOL_UDP:
        return AsyncModbusUdpClient(host=host, port=port, framer=FramerType.SOCKET)
    if protocol == PROTOCOL_TCP:
        return AsyncModbusTcpClient(host=host, port=port, framer=FramerType.SOCKET)
    # RTU over TCP
    return AsyncModbusTcpClient(host=host, port=port, framer=FramerType.RTU)


async def _test_connection(host: str, port: int, slave_id: int, protocol: str) -> str | None:
    """Test Modbus connection. Returns error key or None on success."""
    client = _create_client(host, port, protocol)
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


def _build_register_schema(defaults: dict[str, int | str]) -> vol.Schema:
    """Build a vol.Schema for register address and name configuration."""
    sensor_fields: dict = {}
    for desc in SENSOR_DESCRIPTIONS:
        nkey = f"{desc.key}_name"
        akey = f"{desc.key}_address"
        sensor_fields[vol.Required(nkey, default=defaults[nkey])] = str
        sensor_fields[vol.Required(akey, default=defaults[akey])] = int

    binary_sensor_fields: dict = {}
    for desc in BINARY_SENSOR_DESCRIPTIONS:
        nkey = f"{desc.key}_name"
        akey = f"{desc.key}_address"
        binary_sensor_fields[vol.Required(nkey, default=defaults[nkey])] = str
        binary_sensor_fields[vol.Required(akey, default=defaults[akey])] = int

    switch_fields: dict = {}
    for desc in SWITCH_DESCRIPTIONS:
        nkey = f"{desc.key}_name"
        wkey = f"{desc.key}_write_address"
        vkey = f"{desc.key}_verify_address"
        switch_fields[vol.Required(nkey, default=defaults[nkey])] = str
        switch_fields[vol.Required(wkey, default=defaults[wkey])] = int
        switch_fields[vol.Required(vkey, default=defaults[vkey])] = int

    number_fields: dict = {}
    for desc in NUMBER_DESCRIPTIONS:
        nkey = f"{desc.key}_name"
        wkey = f"{desc.key}_write_address"
        vkey = f"{desc.key}_verify_address"
        number_fields[vol.Required(nkey, default=defaults[nkey])] = str
        number_fields[vol.Required(wkey, default=defaults[wkey])] = int
        number_fields[vol.Required(vkey, default=defaults[vkey])] = int

    return vol.Schema(
        {
            vol.Optional("sensors"): section(
                vol.Schema(sensor_fields), {"collapsed": False}
            ),
            vol.Optional("binary_sensors"): section(
                vol.Schema(binary_sensor_fields), {"collapsed": False}
            ),
            vol.Optional("switches"): section(
                vol.Schema(switch_fields), {"collapsed": False}
            ),
            vol.Optional("numbers"): section(
                vol.Schema(number_fields), {"collapsed": False}
            ),
        }
    )


class WanasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wanas."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._connection_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _test_connection(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_SLAVE_ID],
                user_input[CONF_PROTOCOL],
            )
            if error:
                errors["base"] = error
            else:
                show_advanced = user_input.pop(CONF_SHOW_ADVANCED, False)
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE_ID]}"
                )
                self._abort_if_unique_id_configured()

                if show_advanced:
                    self._connection_data = user_input
                    return await self.async_step_registers()

                return self.async_create_entry(
                    title=f"Wanas ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_registers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle advanced register address configuration."""
        defaults = get_default_register_config()

        if user_input is not None:
            # Flatten nested section data into a single dict
            flat: dict[str, Any] = {}
            for value in user_input.values():
                if isinstance(value, dict):
                    flat.update(value)
            return self.async_create_entry(
                title=f"Wanas ({self._connection_data[CONF_HOST]})",
                data=self._connection_data,
                options={CONF_REGISTERS: flat},
            )

        return self.async_show_form(
            step_id="registers",
            data_schema=_build_register_schema(defaults),
        )
