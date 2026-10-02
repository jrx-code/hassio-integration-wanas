"""Time platform for Wanas integration: where each schedule period ends."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import SCHEDULE_PERIOD_UNTIL_ADDRESSES
from .coordinator import WanasCoordinator
from .entity import device_info, device_key
from .schedule import DAY_MINUTES, boundary_error, format_minutes

# Writes share one RS485 bus, so let Home Assistant serialise service calls.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the four period boundaries."""
    coordinator: WanasCoordinator = entry.runtime_data
    async_add_entities(
        WanasPeriodUntil(coordinator, entry, period)
        for period in range(1, len(SCHEDULE_PERIOD_UNTIL_ADDRESSES) + 1)
    )


class WanasPeriodUntil(CoordinatorEntity[WanasCoordinator], TimeEntity):
    """End of period N (1-4) on the selected schedule day; also the start of period N+1.

    Registers 10-13 hold minutes after midnight in quarter hours. Period 5 runs to
    midnight and period 1 starts at midnight, so neither has an entity, as on the panel.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry, period: int) -> None:
        """Initialize the boundary entity."""
        super().__init__(coordinator)
        self._period = period
        self._address = SCHEDULE_PERIOD_UNTIL_ADDRESSES[period - 1]
        self._attr_unique_id = f"{device_key(entry)}_period_{period}_until"
        self._attr_translation_key = f"period_{period}_until"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> time | None:
        """Return the boundary as a time of day."""
        data = self.coordinator.data
        if not data or (minutes := data.get(self._address)) is None:
            return None
        if not 0 <= minutes < DAY_MINUTES:
            return None
        return time(minutes // 60, minutes % 60)

    async def async_set_value(self, value: time) -> None:
        """Move the boundary, keeping the quarter-hour grid and the period order."""
        minutes = value.hour * 60 + value.minute
        if value.second or value.microsecond:
            minutes += 1  # fails the grid check below, with the time in the message
        if error := boundary_error(minutes):
            raise ServiceValidationError(f"Period {self._period} until: {error}")

        data = self.coordinator.data or {}
        earlier = data.get(self._address - 1) if self._period > 1 else 0
        later = (
            data.get(self._address + 1)
            if self._period < len(SCHEDULE_PERIOD_UNTIL_ADDRESSES)
            else DAY_MINUTES
        )
        if earlier is not None and minutes <= earlier:
            raise ServiceValidationError(
                f"Period {self._period} cannot end at {format_minutes(minutes)}: "
                f"period {self._period - 1} already ends at {format_minutes(earlier)}"
            )
        if later is not None and minutes >= later:
            raise ServiceValidationError(
                f"Period {self._period} cannot end at {format_minutes(minutes)}: "
                f"period {self._period + 1} ends at {format_minutes(later)}"
            )
        await self.coordinator.async_write_register(self._address, minutes)
