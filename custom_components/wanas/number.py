"""Number platform for Wanas integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUMBER_DESCRIPTIONS, WanasNumberDescription
from .coordinator import WanasCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wanas number entities."""
    coordinator: WanasCoordinator = entry.runtime_data
    async_add_entities(
        WanasNumber(coordinator, entry, desc) for desc in NUMBER_DESCRIPTIONS
    )


class WanasNumber(CoordinatorEntity[WanasCoordinator], NumberEntity):
    """Representation of a Wanas number entity."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: WanasCoordinator,
        entry: ConfigEntry,
        description: WanasNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_name = coordinator.registers.get(
            f"{description.key}_name", description.name
        )
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wanas Rekuperator",
            manufacturer="Wanas",
        )

    @property
    def _write_address(self) -> int:
        """Return the effective write address."""
        return self.coordinator.registers.get(
            f"{self._description.key}_write_address", self._description.write_address
        )

    @property
    def _verify_address(self) -> int:
        """Return the effective verify address."""
        return self.coordinator.registers.get(
            f"{self._description.key}_verify_address", self._description.verify_address
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._verify_address)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        await self.coordinator.async_write_register(
            self._write_address, int(value)
        )
