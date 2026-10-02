"""Switch platform for Wanas integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import SWITCH_DESCRIPTIONS, WanasSwitchDescription
from .coordinator import WanasCoordinator
from .entity import device_info, device_key

# Writes share one RS485 bus, so let Home Assistant serialise service calls.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wanas switch entities."""
    coordinator: WanasCoordinator = entry.runtime_data
    async_add_entities(
        WanasSwitch(coordinator, entry, desc)
        for desc in SWITCH_DESCRIPTIONS
        if coordinator.has_feature(desc.feature)
    )


class WanasSwitch(CoordinatorEntity[WanasCoordinator], SwitchEntity):
    """Representation of a Wanas switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WanasCoordinator,
        entry: ConfigEntry,
        description: WanasSwitchDescription,
    ) -> None:
        """Initialize the switch."""
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
        self._attr_entity_category = description.entity_category
        self._attr_device_info = device_info(entry)

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
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._verify_address)
        if value is None:
            return None
        return value != self._description.off_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_write_register(
            self._write_address, self._description.on_value
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_write_register(
            self._write_address, self._description.off_value
        )
