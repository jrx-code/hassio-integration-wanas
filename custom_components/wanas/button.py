"""Button platform for Wanas integration: set the controller clock from Home Assistant."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .clock import encode_clock
from .const import CLOCK_DATE_ADDRESS, CLOCK_TIME_ADDRESS
from .coordinator import WanasCoordinator
from .entity import device_info, device_key

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the clock sync button."""
    async_add_entities([WanasSyncClockButton(entry.runtime_data, entry)])


class WanasSyncClockButton(CoordinatorEntity[WanasCoordinator], ButtonEntity):
    """Write Home Assistant's local date and time into registers 50 and 51."""

    _attr_has_entity_name = True
    _attr_translation_key = "sync_clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_sync_clock"
        self._attr_device_info = device_info(entry)

    async def async_press(self) -> None:
        """Set the controller clock to the current local time."""
        date_value, time_value = encode_clock(dt_util.now())
        await self.coordinator.async_write_registers(
            {CLOCK_DATE_ADDRESS: date_value, CLOCK_TIME_ADDRESS: time_value}
        )
