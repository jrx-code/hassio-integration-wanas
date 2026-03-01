"""Binary sensor platform for Wanas integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSOR_DESCRIPTIONS, DOMAIN, WanasBinarySensorDescription
from .coordinator import WanasCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wanas binary sensor entities."""
    coordinator: WanasCoordinator = entry.runtime_data
    async_add_entities(
        WanasBinarySensor(coordinator, entry, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class WanasBinarySensor(CoordinatorEntity[WanasCoordinator], BinarySensorEntity):
    """Representation of a Wanas binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WanasCoordinator,
        entry: ConfigEntry,
        description: WanasBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_name = coordinator.registers.get(
            f"{description.key}_name", description.name
        )
        self._attr_device_class = description.device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wanas Rekuperator",
            manufacturer="Wanas",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None
        address = self.coordinator.registers.get(
            f"{self._description.key}_address", self._description.address
        )
        value = self.coordinator.data.get(address)
        if value is None:
            return None
        return value != 0
