"""Read blocking, bus serialisation and error mapping."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wanas.const import (
    CONF_HAS_COOLER,
    CONF_HAS_HEATER,
    CONF_HAS_HUMIDIFIER,
    CONF_HAS_MAXICONTROL,
    DOMAIN,
)
from custom_components.wanas.coordinator import _build_read_blocks

from .conftest import CONNECTION


def test_blocks_never_exceed_the_cap() -> None:
    """A long contiguous run is split, because gateways stop answering long reads."""
    blocks = _build_read_blocks(list(range(0, 40)))
    assert all(count <= 16 for _, count in blocks)
    covered = {addr for start, count in blocks for addr in range(start, start + count)}
    assert set(range(0, 40)) <= covered


def test_blocks_merge_small_gaps_and_split_large_ones() -> None:
    """Addresses three apart share a request; a wide gap starts a new one."""
    assert _build_read_blocks([0, 1, 2]) == [(0, 3)]
    assert _build_read_blocks([0, 3]) == [(0, 4)]
    assert _build_read_blocks([0, 30]) == [(0, 1), (30, 1)]


async def test_writes_and_reads_never_overlap(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Only one exchange may be on the bus at a time.

    RTU frames carry no transaction id and the gateway is transparent, so an
    overlapping request cannot be told apart from someone else's answer.
    """
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    in_flight = 0
    peak = 0

    async def slow(*args, **kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0)
        in_flight -= 1
        ok = MagicMock()
        ok.isError.return_value = False
        ok.registers = [0] * kwargs.get("count", 1)
        return ok

    mock_client.write_register = AsyncMock(side_effect=slow)
    mock_client.read_holding_registers = AsyncMock(side_effect=slow)

    await asyncio.gather(
        coordinator.async_write_register(38, 1),
        coordinator.async_write_register(39, 1),
        coordinator.async_write_register(40, 1),
        coordinator.async_refresh(),
    )

    assert peak == 1


async def test_rejected_write_raises_a_user_facing_error(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """A device refusal is a HomeAssistantError, not a coordinator update failure."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    refused = MagicMock()
    refused.isError.return_value = True
    mock_client.write_register = AsyncMock(return_value=refused)

    with pytest.raises(HomeAssistantError, match="rejected the write"):
        await config_entry.runtime_data.async_write_register(39, 1)


async def test_failed_write_closes_the_socket(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """A dropped client is closed, otherwise the gateway runs out of sockets."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    mock_client.close.reset_mock()
    mock_client.write_register = AsyncMock(side_effect=OSError("boom"))
    with pytest.raises(HomeAssistantError):
        await coordinator.async_write_register(39, 1)

    mock_client.close.assert_called()


async def test_absent_module_is_reported_by_the_coordinator(
    hass: HomeAssistant, mock_client
) -> None:
    """Feature gating is readable from the coordinator, which the platforms rely on."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="192.0.2.10:5503:1",
        data={
            **CONNECTION,
            CONF_HAS_HEATER: True,
            CONF_HAS_COOLER: False,
            CONF_HAS_HUMIDIFIER: True,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data
    assert coordinator.features[CONF_HAS_COOLER] is False
    assert coordinator.has_feature(CONF_HAS_COOLER) is False
    assert coordinator.has_feature(CONF_HAS_HEATER) is True
    assert coordinator.has_feature(None) is True


@pytest.mark.parametrize("fitted", [False, True])
async def test_maxicontrol_registers_follow_the_module(
    hass: HomeAssistant, mock_client, fitted: bool
) -> None:
    """Registers 55-57 and 65-67 are only polled when the room panels are declared."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="192.0.2.10:5503:1",
        data={**CONNECTION, CONF_HAS_MAXICONTROL: fitted},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    blocks = entry.runtime_data.read_blocks
    covered = {addr for start, count in blocks for addr in range(start, start + count)}
    panel = {55, 56, 57, 65, 66, 67}
    assert (panel <= covered) is fitted
    assert not fitted or all(count <= 16 for _, count in blocks)
    if not fitted:
        assert not panel & covered


async def test_a_call_that_never_returns_releases_the_bus(
    hass: HomeAssistant, config_entry, mock_client, monkeypatch
) -> None:
    """A hung read times out, drops the socket and lets the next write through.

    Without the deadline the lock stays held and every later exchange waits forever,
    which is how the core modbus hub froze on the real unit.
    """
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data
    monkeypatch.setattr("custom_components.wanas.coordinator.BUS_TIMEOUT", 0.05)

    async def hang(*args, **kwargs):
        await asyncio.Event().wait()

    healthy = mock_client.read_holding_registers.side_effect
    mock_client.read_holding_registers.side_effect = hang
    mock_client.close.reset_mock()
    await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    mock_client.close.assert_called()

    mock_client.read_holding_registers.side_effect = healthy
    await asyncio.wait_for(coordinator.async_write_register(39, 1), 1)
    mock_client.write_register.assert_awaited()


async def test_repeated_failed_polls_start_a_new_connection(
    hass: HomeAssistant, config_entry, mock_client
) -> None:
    """Error responses keep the socket, but not for more than three polls in a row."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data
    assert coordinator.failed_polls == 0
    assert coordinator.last_poll_success is not None

    healthy = mock_client.read_holding_registers.side_effect
    refused = MagicMock()
    refused.isError.return_value = True
    mock_client.read_holding_registers.side_effect = None
    mock_client.read_holding_registers.return_value = refused
    mock_client.close.reset_mock()

    for _ in range(2):
        await coordinator.async_refresh()
    mock_client.close.assert_not_called()
    await coordinator.async_refresh()
    assert coordinator.failed_polls == 3
    mock_client.close.assert_called_once()

    mock_client.read_holding_registers.side_effect = healthy
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert coordinator.failed_polls == 0
