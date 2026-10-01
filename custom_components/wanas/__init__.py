"""The Wanas integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    DOMAIN,
    NUMBER_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
    SWITCH_DESCRIPTIONS,
)
from .coordinator import WanasCoordinator
from .entity import device_key

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

type WanasConfigEntry = ConfigEntry[WanasCoordinator]


def _purge_absent_modules(hass: HomeAssistant, entry: WanasConfigEntry) -> None:
    """Drop registry entries for modules the unit does not have.

    Without this, answering "no" to a module the user first said yes to would leave
    its entities behind as permanently unavailable.
    """
    coordinator: WanasCoordinator = entry.runtime_data
    absent = {
        f"{device_key(entry)}_{desc.key}"
        for desc in (
            *SENSOR_DESCRIPTIONS,
            *BINARY_SENSOR_DESCRIPTIONS,
            *SWITCH_DESCRIPTIONS,
            *NUMBER_DESCRIPTIONS,
        )
        if not coordinator.has_feature(desc.feature)
    }
    if not absent:
        return

    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id in absent:
            registry.async_remove(reg_entry.entity_id)


async def async_migrate_entry(hass: HomeAssistant, entry: WanasConfigEntry) -> bool:
    """Move entity unique ids off entry_id and onto the stable host:port:slave id.

    Entities keyed by entry_id are orphaned whenever the integration is removed and
    added again, taking their history with them. The config flow has always stored a
    stable unique_id, so version 2 simply re-keys what is already in the registry.
    """
    if entry.version >= 2:
        return True

    stable = device_key(entry)
    if stable != entry.entry_id:
        registry = er.async_get(hass)
        old_prefix = f"{entry.entry_id}_"
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg_entry.unique_id.startswith(old_prefix):
                registry.async_update_entity(
                    reg_entry.entity_id,
                    new_unique_id=f"{stable}_{reg_entry.unique_id[len(old_prefix):]}",
                )

        device_registry = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
            if (DOMAIN, entry.entry_id) in device.identifiers:
                device_registry.async_update_device(
                    device.id,
                    new_identifiers={(DOMAIN, stable)},
                )

    hass.config_entries.async_update_entry(entry, version=2)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: WanasConfigEntry) -> None:
    """Reload when the fitted modules change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: WanasConfigEntry) -> bool:
    """Set up Wanas from a config entry."""
    coordinator = WanasCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    _purge_absent_modules(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WanasConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: WanasCoordinator = entry.runtime_data
        await coordinator.async_close()

    return unload_ok
