"""Services for reading and writing the Wanas weekly schedule."""

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
    SCHEDULE_PERIOD_SPEED_ADDRESSES,
    SCHEDULE_PERIOD_TEMPERATURE_ADDRESSES,
    SCHEDULE_PERIOD_UNTIL_ADDRESSES,
)
from .coordinator import WanasCoordinator
from .schedule import PERIOD_COUNT, boundary_error, day_periods, order_error

SERVICE_GET_SCHEDULE = "get_schedule"
SERVICE_SET_SCHEDULE = "set_schedule"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DAYS = "days"
ATTR_PERIODS = "periods"
ATTR_UNTIL = "until"
ATTR_SPEED = "speed"
ATTR_TEMPERATURE = "temperature"


def _until(value: Any) -> int:
    """Accept "06:30" for a period end and return minutes after midnight."""
    if not isinstance(value, str) or ":" not in value:
        raise vol.Invalid(f"until {value!r} must be HH:MM")
    hours, _, minutes = value.partition(":")
    try:
        total = int(hours) * 60 + int(minutes)
    except ValueError as err:
        raise vol.Invalid(f"until {value!r} must be HH:MM") from err
    if error := boundary_error(total):
        raise vol.Invalid(f"until {error}")
    return total


PERIOD_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_UNTIL): _until,
        vol.Required(ATTR_SPEED): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
        vol.Required(ATTR_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=10, max=30)),
    }
)


def _periods(value: Any) -> list[dict[str, int]]:
    """Five periods; 1-4 need an until, 5 runs to midnight and must not have one."""
    periods = [PERIOD_SCHEMA(item) for item in cv.ensure_list(value)]
    if len(periods) != PERIOD_COUNT:
        raise vol.Invalid(f"periods must list all {PERIOD_COUNT} periods of the day")
    for number, period in enumerate(periods, start=1):
        if number < PERIOD_COUNT and ATTR_UNTIL not in period:
            raise vol.Invalid(f"period {number} needs until")
        if number == PERIOD_COUNT and ATTR_UNTIL in period:
            raise vol.Invalid("period 5 runs to midnight, leave out until")
    if error := order_error([period[ATTR_UNTIL] for period in periods[:-1]]):
        raise vol.Invalid(error)
    return periods


GET_SCHEDULE_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})

# Schema errors become a 400 on the REST API; ServiceValidationError raised in the
# handler does not, so everything checkable without the bus is checked here.
SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_DAYS): vol.All(
            cv.ensure_list, [vol.In(SCHEDULE_DAYS)], vol.Length(min=1)
        ),
        vol.Required(ATTR_PERIODS): _periods,
    }
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


async def _get_schedule(call: ServiceCall) -> ServiceResponse:
    coordinator = _coordinator(call.hass, call)
    week = await coordinator.async_read_week()
    return {
        SCHEDULE_DAYS[day]: {ATTR_PERIODS: day_periods(values)}
        for day, values in week.items()
    }


async def _set_schedule(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass, call)
    periods: list[dict[str, int]] = call.data[ATTR_PERIODS]
    values: dict[int, int] = {}
    for index, period in enumerate(periods):
        if index < len(SCHEDULE_PERIOD_UNTIL_ADDRESSES):
            values[SCHEDULE_PERIOD_UNTIL_ADDRESSES[index]] = period[ATTR_UNTIL]
        values[SCHEDULE_PERIOD_SPEED_ADDRESSES[index]] = period[ATTR_SPEED]
        values[SCHEDULE_PERIOD_TEMPERATURE_ADDRESSES[index]] = period[ATTR_TEMPERATURE]
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
