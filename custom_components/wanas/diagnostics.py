"""Diagnostics support for the Wanas integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import WanasCoordinator

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: WanasCoordinator = entry.runtime_data
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    register_addresses = {
        key: value
        for key, value in coordinator.registers.items()
        if key.endswith("_address") and isinstance(value, int)
    }

    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "domain": entry.domain,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "protocol": entry.data.get(CONF_PROTOCOL),
        "slave_id": entry.data.get(CONF_SLAVE_ID),
        "scan_interval": scan_interval,
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None
        ),
        "register_addresses": register_addresses,
        "read_blocks": [
            {"start": start, "count": count}
            for start, count in coordinator.read_blocks
        ],
        "last_update_success": coordinator.last_update_success,
        "data_keys": sorted(coordinator.data.keys()) if coordinator.data else [],
    }
