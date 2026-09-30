"""Shared identity helpers for Wanas entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_PROTOCOL, CONF_SLAVE_ID, DEFAULT_PROTOCOL, DOMAIN


def device_key(entry: ConfigEntry) -> str:
    """Stable identity for this unit.

    The config flow already sets a unique_id of host:port:slave_id, which survives
    removing and re-adding the integration. entry_id does not, and using it means a
    re-add orphans every entity together with its history. Older entries created
    before the migration may still have no unique_id, hence the fallback.
    """
    return entry.unique_id or entry.entry_id


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device registry entry shared by every platform."""
    host = entry.data.get("host", "")
    port = entry.data.get("port", "")
    slave = entry.data.get(CONF_SLAVE_ID, "")
    protocol = entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
    return DeviceInfo(
        identifiers={(DOMAIN, device_key(entry))},
        name="Wanas Rekuperator",
        manufacturer="Wanas",
        # The controller exposes no model or firmware register, so the connection
        # itself is the most specific thing that can honestly be shown here.
        model=f"HRV over Modbus ({protocol})",
        configuration_url=f"http://{host}" if host else None,
        serial_number=f"{host}:{port}:{slave}" if host else None,
    )
