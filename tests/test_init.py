"""Setup, migration and the optional-module gating."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wanas.const import (
    CONF_HAS_COOLER,
    CONF_HAS_HEATER,
    CONF_HAS_HUMIDIFIER,
    CONF_HAS_MAXICONTROL,
    DOMAIN,
)

from .conftest import ALL_MODULES, CONNECTION

# 51 register entities plus the controller clock, program day select and clock button.
FULL_SET = 54
COOLER_ENTITIES = 3
HUMIDIFIER_ENTITIES = 2
MAXICONTROL_ENTITIES = 6


async def test_setup_creates_every_entity(hass: HomeAssistant, config_entry, mock_client) -> None:
    """A fully equipped unit gets the whole entity set."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        er.async_get(hass), config_entry.entry_id
    )
    assert len(entities) == FULL_SET


async def test_absent_modules_are_not_created(hass: HomeAssistant, mock_client) -> None:
    """Clearing a module removes exactly its entities, and no others."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="192.0.2.10:5503:1",
        data={**CONNECTION, CONF_HAS_HEATER: True, CONF_HAS_COOLER: False,
              CONF_HAS_HUMIDIFIER: False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(entities) == FULL_SET - COOLER_ENTITIES - HUMIDIFIER_ENTITIES

    assert not any("cooler" in e.unique_id for e in entities)
    assert not any("humidifier" in e.unique_id for e in entities)
    assert any("heater" in e.unique_id for e in entities)


async def test_turning_a_module_off_removes_its_entities(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Options that drop a module purge it rather than leaving it unavailable."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert any(
        "cooler" in e.unique_id
        for e in er.async_entries_for_config_entry(registry, config_entry.entry_id)
    )

    hass.config_entries.async_update_entry(
        config_entry, options={**ALL_MODULES, CONF_HAS_COOLER: False}
    )
    await hass.async_block_till_done()

    assert not any(
        "cooler" in e.unique_id
        for e in er.async_entries_for_config_entry(registry, config_entry.entry_id)
    )


async def test_maxicontrol_is_off_unless_declared(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Entries that never answered the maxiCONTROL question keep their entity set."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)
    assert len(entities) == FULL_SET
    assert not any(e.unique_id.endswith("_room_temperature") for e in entities)

    hass.config_entries.async_update_entry(
        config_entry, options={**ALL_MODULES, CONF_HAS_MAXICONTROL: True}
    )
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)
    assert len(entities) == FULL_SET + MAXICONTROL_ENTITIES
    room = hass.states.get(
        registry.async_get_entity_id("sensor", DOMAIN, "192.0.2.10:5503:1_room_temperature")
    )
    # The mock answers each address with its own number: register 65 -> 6.5 degC.
    assert float(room.state) == 6.5


async def test_migration_rekeys_entities_and_device(hass: HomeAssistant, mock_client) -> None:
    """Version 1 entries move off entry_id onto the stable id, keeping their entities."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, unique_id="192.0.2.10:5503:1",
        data={**CONNECTION, **ALL_MODULES},
    )
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}
    )
    legacy = registry.async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_supply_airflow",
        config_entry=entry, device_id=device.id,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    migrated = registry.async_get(legacy.entity_id)
    assert migrated is not None
    assert migrated.unique_id == "192.0.2.10:5503:1_supply_airflow"
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert [d.identifiers for d in devices] == [{(DOMAIN, "192.0.2.10:5503:1")}]


async def test_unload(hass: HomeAssistant, config_entry, mock_client) -> None:
    """Unloading closes the Modbus client."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_client.close.assert_called()
