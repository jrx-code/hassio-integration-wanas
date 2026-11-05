"""Opt-in automatic controller clock sync."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.wanas_community.clock import encode_clock
from custom_components.wanas_community.const import CLOCK_DATE_ADDRESS, CLOCK_TIME_ADDRESS

WARSAW = ZoneInfo("Europe/Warsaw")


def _auto_sync_entity_id(hass: HomeAssistant) -> str:
    registry = er.async_get(hass)
    entry = next(
        e for e in registry.entities.values() if e.unique_id.endswith("_auto_sync_clock")
    )
    return entry.entity_id


async def _setup(hass, config_entry, mock_client):
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_auto_sync_switch_defaults_off(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """The switch is off until the user enables it."""
    await _setup(hass, config_entry, mock_client)
    state = hass.states.get(_auto_sync_entity_id(hass))
    assert state is not None
    assert state.state == STATE_OFF


async def test_auto_sync_corrects_when_drift_exceeds_threshold(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Turning the switch on writes the clock when the controller is skewed."""
    await _setup(hass, config_entry, mock_client)
    coordinator = config_entry.runtime_data

    now = datetime(2026, 11, 6, 12, 0, tzinfo=WARSAW)
    skewed = now - timedelta(minutes=5)
    date_value, time_value = encode_clock(skewed)

    async def read(address, count, device_id):  # noqa: ARG001
        result = MagicMock()
        result.isError.return_value = False
        if address == CLOCK_DATE_ADDRESS and count == 2:
            result.registers = [date_value, time_value]
        else:
            result.registers = [address + i for i in range(count)]
        return result

    mock_client.read_holding_registers.side_effect = read
    mock_client.write_register.reset_mock()

    with patch.object(dt_util, "now", return_value=now):
        assert await coordinator.async_sync_clock_if_drifted(threshold_seconds=60)

    written = {
        call.kwargs["address"]: call.kwargs["value"]
        for call in mock_client.write_register.await_args_list
    }
    expect_date, expect_time = encode_clock(now)
    assert written[CLOCK_DATE_ADDRESS] == expect_date
    assert written[CLOCK_TIME_ADDRESS] == expect_time


async def test_auto_sync_skips_when_within_threshold(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """No write when the controller clock is already close enough."""
    await _setup(hass, config_entry, mock_client)
    coordinator = config_entry.runtime_data

    now = datetime(2026, 11, 6, 12, 0, tzinfo=WARSAW)
    date_value, time_value = encode_clock(now)

    async def read(address, count, device_id):  # noqa: ARG001
        result = MagicMock()
        result.isError.return_value = False
        if address == CLOCK_DATE_ADDRESS and count == 2:
            result.registers = [date_value, time_value]
        else:
            result.registers = [address + i for i in range(count)]
        return result

    mock_client.read_holding_registers.side_effect = read
    mock_client.write_register.reset_mock()

    with patch.object(dt_util, "now", return_value=now):
        assert not await coordinator.async_sync_clock_if_drifted(threshold_seconds=60)

    mock_client.write_register.assert_not_called()


async def test_turning_auto_sync_on_runs_immediate_check(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Turning the switch on both enables the interval and checks once immediately."""
    await _setup(hass, config_entry, mock_client)
    entity_id = _auto_sync_entity_id(hass)

    with patch(
        "custom_components.wanas_community.coordinator.WanasCoordinator.async_sync_clock_if_drifted",
        return_value=False,
    ) as sync:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": entity_id}, blocking=True
        )
        await hass.async_block_till_done()
        sync.assert_awaited()

    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF
