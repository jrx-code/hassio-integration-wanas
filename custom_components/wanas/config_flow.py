"""Config flow for the Wanas integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import section

from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    CONF_CONFIGURE_REGISTERS,
    CONF_PROTOCOL,
    CONF_REGISTERS,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_ADVANCED,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DEFAULT_PROTOCOL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    NUMBER_DESCRIPTIONS,
    PROTOCOL_OPTIONS,
    SENSOR_DESCRIPTIONS,
    SWITCH_DESCRIPTIONS,
    get_default_register_config,
)
from .modbus_client import async_test_connection

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
        vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(PROTOCOL_OPTIONS),
        vol.Optional(CONF_SHOW_ADVANCED, default=False): bool,
    }
)


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


def _flatten_register_sections(user_input: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested section data into a single dict."""
    flat: dict[str, Any] = {}
    for value in user_input.values():
        if isinstance(value, dict):
            flat.update(value)
    return flat


class WanasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wanas."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._connection_data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return WanasOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await async_test_connection(
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
            flat = _flatten_register_sections(user_input)
            return self.async_create_entry(
                title=f"Wanas ({self._connection_data[CONF_HOST]})",
                data=self._connection_data,
                options={CONF_REGISTERS: flat},
            )

        return self.async_show_form(
            step_id="registers",
            data_schema=_build_register_schema(defaults),
        )


class WanasOptionsFlowHandler(OptionsFlow):
    """Handle Wanas options."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        current = self.config_entry.options
        current_interval = current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        if user_input is not None:
            configure_registers = user_input.pop(CONF_CONFIGURE_REGISTERS, False)
            self._options = {
                CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
            }
            # Preserve existing register map unless the user re-edits it
            if CONF_REGISTERS in current:
                self._options[CONF_REGISTERS] = current[CONF_REGISTERS]
            if configure_registers:
                return await self.async_step_registers()
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(CONF_CONFIGURE_REGISTERS, default=False): bool,
                }
            ),
        )

    async def async_step_registers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-edit register addresses and names."""
        defaults = {
            **get_default_register_config(),
            **self.config_entry.options.get(CONF_REGISTERS, {}),
        }

        if user_input is not None:
            flat = _flatten_register_sections(user_input)
            self._options[CONF_REGISTERS] = flat
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="registers",
            data_schema=_build_register_schema(defaults),
        )
