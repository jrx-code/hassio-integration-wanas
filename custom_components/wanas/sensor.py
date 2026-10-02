"""Sensor platform for Wanas integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .clock import decode_clock
from .const import (
    CLOCK_DATE_ADDRESS,
    CLOCK_TIME_ADDRESS,
    SENSOR_DESCRIPTIONS,
    WanasSensorDescription,
)
from .coordinator import WanasCoordinator
from .entity import device_info, device_key

# Read-only, values come from the coordinator.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wanas sensor entities."""
    coordinator: WanasCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        WanasSensor(coordinator, entry, desc)
        for desc in SENSOR_DESCRIPTIONS
        if coordinator.has_feature(desc.feature)
    ]
    entities.append(WanasClockSensor(coordinator, entry))
    async_add_entities(entities)


class WanasSensor(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """Representation of a Wanas sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WanasCoordinator,
        entry: ConfigEntry,
        description: WanasSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._description = description
        self._attr_unique_id = f"{device_key(entry)}_{description.key}"
        self._attr_translation_key = description.key
        # Setting _attr_name at all wins over translation_key in Entity._name_internal,
        # so only set it when the advanced register options carry a name the user
        # actually changed. Otherwise the translated name is used.
        name = coordinator.registers.get(f"{description.key}_name", description.name)
        if name != description.name:
            self._attr_name = name
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        address = self.coordinator.registers.get(
            f"{self._description.key}_address", self._description.address
        )
        return WanasCoordinator.get_sensor_value(
            self.coordinator.data,
            address,
            self._description.data_type,
            self._description.scale,
        )


class WanasClockSensor(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """The controller's own clock (registers 50 and 51), which the weekly program runs on.

    It drifts - minutes per week on the unit this was written against - and nothing
    sets it except the panel or the sync button, so it is worth being able to see.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "controller_clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the clock sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_controller_clock"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> datetime | None:
        """Return the controller time as an aware datetime."""
        data = self.coordinator.data
        if not data or CLOCK_DATE_ADDRESS not in data or CLOCK_TIME_ADDRESS not in data:
            return None
        return decode_clock(
            data[CLOCK_DATE_ADDRESS],
            data[CLOCK_TIME_ADDRESS],
            dt_util.get_default_time_zone(),
        )
