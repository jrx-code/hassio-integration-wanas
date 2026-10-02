"""Select platform for Wanas integration: which day the weekly program entities edit."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import SCHEDULE_DAY_ADDRESS, SCHEDULE_DAYS
from .coordinator import WanasCoordinator
from .entity import device_info, device_key

# Writes share one RS485 bus, so let Home Assistant serialise service calls.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the program day selector."""
    async_add_entities([WanasProgramDaySelect(entry.runtime_data, entry)])


class WanasProgramDaySelect(CoordinatorEntity[WanasCoordinator], SelectEntity):
    """Register 8: the day the zone end, speed and temperature entities show and write.

    The controller has one window of registers (10-23) onto a seven-day program, and
    register 8 picks the day behind it. Changing this does not change what the unit
    runs today, only which day the fourteen zone entities are looking at.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "program_day"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(SCHEDULE_DAYS)

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the selector."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_program_day"
        self._attr_device_info = device_info(entry)

    @property
    def current_option(self) -> str | None:
        """Return the selected program day."""
        if self.coordinator.data is None:
            return None
        day = self.coordinator.data.get(SCHEDULE_DAY_ADDRESS)
        if day is None or not 0 <= day < len(SCHEDULE_DAYS):
            return None
        return SCHEDULE_DAYS[day]

    async def async_select_option(self, option: str) -> None:
        """Point the program window at another day."""
        await self.coordinator.async_write_register(
            SCHEDULE_DAY_ADDRESS, SCHEDULE_DAYS.index(option)
        )
