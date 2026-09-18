"""The Wanas integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import WanasCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

type WanasConfigEntry = ConfigEntry[WanasCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: WanasConfigEntry) -> bool:
    """Set up Wanas from a config entry."""
    coordinator = WanasCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WanasConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: WanasCoordinator = entry.runtime_data
        await coordinator.async_close()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: WanasConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
