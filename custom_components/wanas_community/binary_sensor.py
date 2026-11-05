"""Binary sensor platform for Wanas integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSOR_DESCRIPTIONS, WanasBinarySensorDescription
from .coordinator import WanasCoordinator
from .entity import device_info, device_key

# Read-only, values come from the coordinator.
PARALLEL_UPDATES = 0

# How many bus_log entries to expose on the connection-status entity.
_BUS_LOG_ATTR_LIMIT = 20


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wanas binary sensor entities."""
    coordinator: WanasCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        WanasBinarySensor(coordinator, entry, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
        if coordinator.has_feature(desc.feature)
    ]
    entities.append(WanasConnectionStatusBinarySensor(coordinator, entry))
    async_add_entities(entities)


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
        self._attr_unique_id = f"{device_key(entry)}_{description.key}"
        self._attr_translation_key = description.key
        # Setting _attr_name at all wins over translation_key in Entity._name_internal,
        # so only set it when the advanced register options carry a name the user
        # actually changed. Otherwise the translated name is used.
        name = coordinator.registers.get(f"{description.key}_name", description.name)
        if name != description.name:
            self._attr_name = name
        self._attr_device_class = description.device_class
        self._attr_entity_category = description.entity_category
        self._attr_device_info = device_info(entry)

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


class WanasConnectionStatusBinarySensor(
    CoordinatorEntity[WanasCoordinator], BinarySensorEntity
):
    """Connectivity to the controller, with the same debug info as diagnostics."""

    _attr_has_entity_name = True
    _attr_translation_key = "connection_status"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the connection-status sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_connection_status"
        self._attr_device_info = device_info(entry)

    @property
    def available(self) -> bool:
        """Always show status, including when the controller is unreachable."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True when the last coordinator update reached the controller."""
        return bool(self.coordinator.last_update_success)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Last poll outcome and a short bus_log, without host or secrets."""
        last = self.coordinator.last_poll_success
        return {
            "last_poll_success": last.isoformat() if last else None,
            "failed_polls_in_a_row": self.coordinator.failed_polls,
            "bus_log": list(self.coordinator.bus_log)[-_BUS_LOG_ATTR_LIMIT:],
        }
