"""Heat recovery: the calculation and the three sensors built on it."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.wanas.const import DOMAIN
from custom_components.wanas.recovery import MODE_COOLING, MODE_HEATING, compute

UID = "192.0.2.10:5503:1"

# Read off the real unit on 2026-10-02: outdoor 15.4, exhaust 20.0, supply 21.6, indoor 24.1.
AUTUMN = {0: 396, 1: 398, 4: 154, 5: 200, 6: 216, 7: 241}


def test_heating_matches_the_real_unit() -> None:
    """Supply side 822 W and 71 %, extract side lower because of fan heat."""
    r = compute(outdoor=15.4, supply=21.6, indoor=24.1, supply_airflow=396,
                exhaust=20.0, exhaust_airflow=398)
    assert r is not None
    assert r.mode == MODE_HEATING
    assert r.power == 822
    assert r.efficiency == 71
    assert r.delta == 6.2
    assert r.extract_power == 547


def test_summer_counts_recovered_cooling() -> None:
    """Outdoor warmer than indoor: the core cools the supply air, power stays positive."""
    r = compute(outdoor=32.0, supply=26.0, indoor=24.0, supply_airflow=300)
    assert r is not None
    assert r.mode == MODE_COOLING
    assert r.power == round(1.2 * 1005 / 3600 * 300 * 6)
    assert r.efficiency == 75


def test_fan_heat_is_not_recovered_cooling() -> None:
    """Supply warmer than a warm outdoor is motor heat, not recovery."""
    r = compute(outdoor=28.0, supply=28.5, indoor=24.0, supply_airflow=300)
    assert r is not None
    assert r.power == 0
    assert r.efficiency == 0


def test_efficiency_unknown_when_indoor_and_outdoor_are_close() -> None:
    """A ratio over a 1 K difference is noise."""
    r = compute(outdoor=22.5, supply=23.0, indoor=23.5, supply_airflow=200)
    assert r is not None
    assert r.efficiency is None
    assert r.power == round(1.2 * 1005 / 3600 * 200 * 0.5)


@pytest.mark.parametrize("supply", [None, -247.0, 85.0])
def test_missing_or_faulty_sensor(supply) -> None:
    """A missing reading or the 63066 fault value gives no result at all."""
    assert compute(outdoor=5.0, supply=supply, indoor=21.0, supply_airflow=200) is None


@pytest.fixture
def regs(mock_client) -> dict[int, int]:
    """Register bank behind the shared client mock: zeros plus whatever a test sets."""
    bank = {addr: 0 for addr in range(80)}
    bank.update(AUTUMN)

    async def read(address, count, device_id):  # noqa: ARG001
        result = MagicMock()
        result.isError.return_value = False
        result.registers = [bank[a] for a in range(address, address + count)]
        return result

    mock_client.read_holding_registers.side_effect = read
    return bank


async def _setup(hass: HomeAssistant, config_entry) -> dict[str, str]:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    return {
        key: registry.async_get_entity_id("sensor", DOMAIN, f"{UID}_{key}")
        for key in ("heat_recovery_power", "heat_recovery_efficiency", "heat_recovery_energy")
    }


async def test_sensors_follow_the_poll(hass: HomeAssistant, config_entry, regs) -> None:
    """Power, efficiency and the attributes come from the registers already read."""
    ids = await _setup(hass, config_entry)
    power = hass.states.get(ids["heat_recovery_power"])
    assert power.state == "822"
    assert power.attributes["unit_of_measurement"] == "W"
    assert power.attributes["mode"] == "heating"
    assert power.attributes["temperature_gain"] == 6.2
    assert power.attributes["extract_side_power"] == 547
    assert hass.states.get(ids["heat_recovery_efficiency"]).state == "71"


@pytest.mark.parametrize("address", [30, 31, 33, 34])  # GWC, bypass, heater, cooler
async def test_unknown_while_something_else_moves_the_supply_temperature(
    hass: HomeAssistant, config_entry, regs, address
) -> None:
    """With the bypass open or a module running, recovery is not measured."""
    regs[address] = 1
    ids = await _setup(hass, config_entry)
    assert hass.states.get(ids["heat_recovery_power"]).state == "unknown"
    assert hass.states.get(ids["heat_recovery_efficiency"]).state == "unknown"


async def test_energy_integrates_between_polls(
    hass: HomeAssistant, config_entry, regs, freezer: FrozenDateTimeFactory
) -> None:
    """Two polls 30 s apart at 822 W add 822 × 30 / 3600 Wh."""
    ids = await _setup(hass, config_entry)
    assert hass.states.get(ids["heat_recovery_energy"]).state == "0.0"

    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    energy = float(hass.states.get(ids["heat_recovery_energy"]).state)
    assert energy == pytest.approx(822 * 30 / 3_600_000, abs=1e-3)


async def test_energy_skips_bypass_time(
    hass: HomeAssistant, config_entry, regs, freezer: FrozenDateTimeFactory
) -> None:
    """Nothing is added across a poll where the bypass was open."""
    ids = await _setup(hass, config_entry)
    regs[31] = 1
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    regs[31] = 0
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert float(hass.states.get(ids["heat_recovery_energy"]).state) == 0.0


async def test_energy_survives_a_restart(hass: HomeAssistant, config_entry, regs) -> None:
    """The total comes back from the restore cache instead of starting at zero."""
    entity_id = "sensor.wanas_rekuperator_recovered_energy"
    mock_restore_cache_with_extra_data(
        hass,
        [(
            State(entity_id, "12.5"),
            {"native_value": 12.5, "native_unit_of_measurement": "kWh"},
        )],
    )
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{UID}_heat_recovery_energy", suggested_object_id="wanas_rekuperator_recovered_energy"
    )
    ids = await _setup(hass, config_entry)
    assert ids["heat_recovery_energy"] == entity_id
    assert float(hass.states.get(entity_id).state) == 12.5
