"""Weekly program behind the day selector, the controller clock and their entities."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.wanas.clock import decode_clock, encode_clock
from custom_components.wanas.const import DOMAIN

WARSAW = ZoneInfo("Europe/Warsaw")
UID = "192.0.2.10:5503:1"


class FakeUnit:
    """A register bank where 10-23 are a window onto the day register 8 selects."""

    def __init__(self) -> None:
        self.regs = {addr: 0 for addr in range(80)}
        # Every day starts as the program read off the real unit: 05:00/08:00/16:00/22:00.
        self.week = {
            day: [300, 480, 960, 1320, 2, 2, 2, 2, 2, 20, 20, 20, 20, 20]
            for day in range(7)
        }
        self.regs[8] = 0
        self.writes: list[tuple[int, int]] = []

    def read(self, address: int, count: int) -> list[int]:
        out = []
        for addr in range(address, address + count):
            if 10 <= addr <= 23:
                out.append(self.week[self.regs[8]][addr - 10])
            else:
                out.append(self.regs[addr])
        return out

    def write(self, address: int, value: int) -> None:
        self.writes.append((address, value))
        if 10 <= address <= 23:
            self.week[self.regs[8]][address - 10] = value
        else:
            self.regs[address] = value


@pytest.fixture
def unit(mock_client) -> FakeUnit:
    """Wire the shared pymodbus mock to a FakeUnit."""
    fake = FakeUnit()

    async def read(address, count, device_id):  # noqa: ARG001
        result = MagicMock()
        result.isError.return_value = False
        result.registers = fake.read(address, count)
        return result

    async def write(address, value, device_id):  # noqa: ARG001
        fake.write(address, value)
        ok = MagicMock()
        ok.isError.return_value = False
        return ok

    mock_client.read_holding_registers = AsyncMock(side_effect=read)
    mock_client.write_register = AsyncMock(side_effect=write)
    return fake


@pytest.fixture
async def loaded(hass: HomeAssistant, config_entry, unit):
    """A set-up entry on top of the FakeUnit."""
    await hass.config.async_set_time_zone("Europe/Warsaw")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{UID}_{key}")
    assert entity_id
    return entity_id


def test_clock_matches_the_values_read_off_the_unit() -> None:
    """3354 / 5408 were read on 2026-10-01 at 21:32; 5402 / 3336 on 2026-10-02 at 13:08."""
    assert decode_clock(3354, 5408, WARSAW) == datetime(2026, 10, 1, 21, 32, tzinfo=WARSAW)
    assert decode_clock(5402, 3336, WARSAW) == datetime(2026, 10, 2, 13, 8, tzinfo=WARSAW)
    assert encode_clock(datetime(2026, 10, 2, 13, 8)) == (5402, 3336)


def test_clock_that_is_not_a_date_reads_as_unknown() -> None:
    """An unset controller (zeros) must not crash the sensor."""
    assert decode_clock(0, 0, WARSAW) is None


async def test_clock_sensor_and_sync_button(
    hass: HomeAssistant, loaded, unit: FakeUnit, freezer
) -> None:
    """The sensor shows registers 50/51; the button writes HA local time into them."""
    unit.regs[50], unit.regs[51] = 5402, 3336
    await loaded.runtime_data.async_refresh()
    await hass.async_block_till_done()

    clock = hass.states.get(_entity_id(hass, "sensor", "controller_clock"))
    assert dt_util.parse_datetime(clock.state) == datetime(2026, 10, 2, 13, 8, tzinfo=WARSAW)

    freezer.move_to("2026-10-02T11:11:30+00:00")  # 13:11 in Warsaw
    await hass.services.async_call(
        "button", "press",
        {"entity_id": _entity_id(hass, "button", "sync_clock")},
        blocking=True,
    )
    assert (unit.regs[50], unit.regs[51]) == (5402, (13 << 8) | 11)


async def test_select_moves_the_program_window(
    hass: HomeAssistant, loaded, unit: FakeUnit
) -> None:
    """Zone entities write to the day the selector points at, and only that day."""
    select_id = _entity_id(hass, "select", "program_day")
    assert hass.states.get(select_id).state == "sunday"

    await hass.services.async_call(
        "select", "select_option", {"entity_id": select_id, "option": "saturday"},
        blocking=True,
    )
    assert unit.regs[8] == 6

    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": _entity_id(hass, "number", "zone_1_speed"), "value": 1},
        blocking=True,
    )
    assert unit.week[6][4] == 1
    assert all(unit.week[day][4] == 2 for day in range(6))


async def test_get_schedule_reads_every_day_and_restores_the_selector(
    hass: HomeAssistant, loaded, unit: FakeUnit
) -> None:
    unit.regs[8] = 3
    unit.week[6][4] = 1

    week = await hass.services.async_call(
        DOMAIN, "get_schedule", {}, blocking=True, return_response=True
    )

    assert set(week) == {
        "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    }
    assert week["saturday"]["zone_speeds"] == [1, 2, 2, 2, 2]
    assert week["monday"] == {
        "zone_ends": [300, 480, 960, 1320],
        "zone_speeds": [2, 2, 2, 2, 2],
        "zone_temperatures": [20, 20, 20, 20, 20],
    }
    assert unit.regs[8] == 3


async def test_set_schedule_writes_only_the_given_days_and_fields(
    hass: HomeAssistant, loaded, unit: FakeUnit
) -> None:
    unit.regs[8] = 5

    await hass.services.async_call(
        DOMAIN, "set_schedule",
        {
            "days": ["monday", "tuesday"],
            "zone_ends": ["06:00", "08:30", 960, "22:15"],
            "zone_speeds": [1, 2, 1, 2, 1],
        },
        blocking=True,
    )

    for day in (1, 2):
        assert unit.week[day][:9] == [360, 510, 960, 1335, 1, 2, 1, 2, 1]
        assert unit.week[day][9:] == [20] * 5  # temperatures were not passed
    for day in (0, 3, 4, 5, 6):
        assert unit.week[day][:4] == [300, 480, 960, 1320]
    assert unit.regs[8] == 5


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"days": ["monday"]}, vol.Invalid),
        ({"days": ["monday"], "zone_ends": ["08:00", "06:00", "16:00", "22:00"]}, vol.Invalid),
        ({"days": ["monday"], "zone_ends": ["05:10", "08:00", "16:00", "22:00"]}, vol.Invalid),
        ({"days": ["monday"], "zone_speeds": [1, 2, 4, 1, 1]}, vol.Invalid),
        ({"days": ["monday"], "zone_temperatures": [20, 20, 20]}, vol.Invalid),
        ({"days": ["funday"], "zone_speeds": [1, 1, 1, 1, 1]}, vol.Invalid),
    ],
)
async def test_set_schedule_rejects_bad_input_without_touching_the_bus(
    hass: HomeAssistant, loaded, unit: FakeUnit, data, error
) -> None:
    unit.writes.clear()
    with pytest.raises(error):
        await hass.services.async_call(DOMAIN, "set_schedule", data, blocking=True)
    assert unit.writes == []


async def test_schedule_call_for_an_unknown_entry_is_refused(
    hass: HomeAssistant, loaded, unit: FakeUnit
) -> None:
    unit.writes.clear()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "get_schedule", {"config_entry_id": "nope"},
            blocking=True, return_response=True,
        )
    assert unit.writes == []


async def test_timed_function_switch_arms_the_longest_run_and_follows_the_countdown(
    hass: HomeAssistant, loaded, unit: FakeUnit
) -> None:
    """Fireplace on writes 180 s; it stays on while register 44 counts down."""
    switch_id = _entity_id(hass, "switch", "fireplace_switch")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch_id}, blocking=True
    )
    assert unit.regs[44] == 180

    unit.regs[44] = 95
    await loaded.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(switch_id).state == "on"

    unit.regs[44] = 0
    await loaded.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(switch_id).state == "off"
