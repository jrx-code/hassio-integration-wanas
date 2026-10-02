"""Diagnostics for the Wanas integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    NUMBER_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
    SWITCH_DESCRIPTIONS,
)
from .coordinator import WanasCoordinator

# unique_id and the device serial number are literally "host:port:slave", so the
# address leaks through them unless they are redacted too.
TO_REDACT = {CONF_HOST, "unique_id", "serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: Any
) -> dict[str, Any]:
    """Return the register bank and how it was read, which is what bug reports need."""
    coordinator: WanasCoordinator = entry.runtime_data

    entities: dict[str, Any] = {}
    for platform, descriptions in (
        ("sensor", SENSOR_DESCRIPTIONS),
        ("binary_sensor", BINARY_SENSOR_DESCRIPTIONS),
        ("switch", SWITCH_DESCRIPTIONS),
        ("number", NUMBER_DESCRIPTIONS),
    ):
        for desc in descriptions:
            addresses = (
                {"address": desc.address}
                if hasattr(desc, "address")
                else {"write": desc.write_address, "verify": desc.verify_address}
            )
            entities[f"{platform}.{desc.key}"] = {
                **addresses,
                "feature": getattr(desc, "feature", None),
                "created": coordinator.has_feature(getattr(desc, "feature", None)),
            }

    return {
        "entry": async_redact_data(
            {
                "version": entry.version,
                "unique_id": entry.unique_id,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "connection": {
            "protocol": coordinator.protocol,
            "port": coordinator.port,
            "slave_id": coordinator.slave_id,
            "scan_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "connected": bool(coordinator._client and coordinator._client.connected),  # noqa: SLF001
        },
        "polling": {
            "read_blocks": [
                {"start": start, "count": count} for start, count in coordinator.read_blocks
            ],
            "last_update_success": coordinator.last_update_success,
            "failed_polls_in_a_row": coordinator.failed_polls,
            "last_poll_success": (
                coordinator.last_poll_success.isoformat()
                if coordinator.last_poll_success
                else None
            ),
        },
        "features": coordinator.features,
        "registers": (
            {str(addr): value for addr, value in sorted(coordinator.data.items())}
            if coordinator.data
            else {}
        ),
        "entities": entities,
    }
