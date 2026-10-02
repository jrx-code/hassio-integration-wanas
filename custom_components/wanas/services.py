"""Services for reading and writing the Wanas weekly program."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SCHEDULE_DAYS,
    SCHEDULE_FIRST_ADDRESS,
    SCHEDULE_ZONE_END_ADDRESSES,
    SCHEDULE_ZONE_SPEED_ADDRESSES,
    SCHEDULE_ZONE_TEMPERATURE_ADDRESSES,
)
from .coordinator import WanasCoordinator

SERVICE_GET_SCHEDULE = "get_schedule"
SERVICE_SET_SCHEDULE = "set_schedule"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DAYS = "days"
ATTR_ZONE_ENDS = "zone_ends"
ATTR_ZONE_SPEEDS = "zone_speeds"
ATTR_ZONE_TEMPERATURES = "zone_temperatures"

# Zone ends are quarter hours; the per-zone limits of the number entities follow
# from the increasing-order check.
ZONE_END_MIN = 15
ZONE_END_MAX = 1425
ZONE_END_STEP = 15


def _minutes(value: Any) -> int:
    """Accept 330 or "05:30" for a zone end and return minutes after midnight."""
    if isinstance(value, str) and ":" in value:
        hours, _, minutes = value.partition(":")
        try:
            value = int(hours) * 60 + int(minutes[:2])
        except ValueError as err:
            raise vol.Invalid(f"zone end {value!r} is not HH:MM") from err
    try:
        minutes_value = int(value)
    except (TypeError, ValueError) as err:
        raise vol.Invalid(f"zone end {value!r} is not a time") from err
    if not ZONE_END_MIN <= minutes_value <= ZONE_END_MAX or minutes_value % ZONE_END_STEP:
        raise vol.Invalid(
            f"zone end {value} must be a quarter hour between 00:15 and 23:45"
        )
    return minutes_value


def _increasing(values: list[int]) -> list[int]:
    """Zone ends must follow each other, or the unit would get an empty or negative zone."""
    if any(later <= earlier for earlier, later in zip(values, values[1:])):
        raise vol.Invalid("zone ends must be in increasing order")
    return values


def _list_of(validator: Any, length: int) -> vol.All:
    return vol.All(cv.ensure_list, [validator], vol.Length(min=length, max=length))


GET_SCHEDULE_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})

SET_SCHEDULE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_DAYS): vol.All(
                cv.ensure_list, [vol.In(SCHEDULE_DAYS)], vol.Length(min=1)
            ),
            vol.Optional(ATTR_ZONE_ENDS): vol.All(_list_of(_minutes, 4), _increasing),
            vol.Optional(ATTR_ZONE_SPEEDS): _list_of(
                vol.All(vol.Coerce(int), vol.Range(min=0, max=3)), 5
            ),
            vol.Optional(ATTR_ZONE_TEMPERATURES): _list_of(
                vol.All(vol.Coerce(int), vol.Range(min=10, max=30)), 5
            ),
        }
    ),
    # Schema errors become a 400 on the REST API; ServiceValidationError raised in
    # the handler does not, so everything checkable without the bus is checked here.
    cv.has_at_least_one_key(ATTR_ZONE_ENDS, ATTR_ZONE_SPEEDS, ATTR_ZONE_TEMPERATURES),
)


def _coordinator(hass: HomeAssistant, call: ServiceCall) -> WanasCoordinator:
    """The coordinator of the entry the call names, or of the only loaded entry."""
    loaded = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        loaded = [entry for entry in loaded if entry.entry_id == entry_id]
    if not loaded:
        raise ServiceValidationError("No loaded Wanas entry matches this call")
    if len(loaded) > 1:
        raise ServiceValidationError(
            "More than one Wanas unit is set up, pass config_entry_id"
        )
    return loaded[0].runtime_data


def _day_program(values: list[int]) -> dict[str, list[int]]:
    """Split the 14 program registers of one day into zones."""

    def pick(addresses: tuple[int, ...]) -> list[int]:
        return [values[address - SCHEDULE_FIRST_ADDRESS] for address in addresses]

    return {
        ATTR_ZONE_ENDS: pick(SCHEDULE_ZONE_END_ADDRESSES),
        ATTR_ZONE_SPEEDS: pick(SCHEDULE_ZONE_SPEED_ADDRESSES),
        ATTR_ZONE_TEMPERATURES: pick(SCHEDULE_ZONE_TEMPERATURE_ADDRESSES),
    }


async def _get_schedule(call: ServiceCall) -> ServiceResponse:
    coordinator = _coordinator(call.hass, call)
    week = await coordinator.async_read_week()
    return {SCHEDULE_DAYS[day]: _day_program(values) for day, values in week.items()}


async def _set_schedule(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass, call)
    values: dict[int, int] = {}
    if (ends := call.data.get(ATTR_ZONE_ENDS)) is not None:
        values.update(zip(SCHEDULE_ZONE_END_ADDRESSES, ends))
    for key, addresses in (
        (ATTR_ZONE_SPEEDS, SCHEDULE_ZONE_SPEED_ADDRESSES),
        (ATTR_ZONE_TEMPERATURES, SCHEDULE_ZONE_TEMPERATURE_ADDRESSES),
    ):
        if (zone_values := call.data.get(key)) is not None:
            values.update(zip(addresses, zone_values))
    days = sorted({SCHEDULE_DAYS.index(day) for day in call.data[ATTR_DAYS]})
    await coordinator.async_write_schedule(days, values)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's services once, whatever the number of entries."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        _get_schedule,
        schema=GET_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_SCHEDULE, _set_schedule, schema=SET_SCHEDULE_SCHEMA
    )
