"""DataUpdateCoordinator for Wanas integration."""

from __future__ import annotations

import asyncio
import ctypes
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import AsyncModbusTcpClient, AsyncModbusUdpClient
from pymodbus.framer import FramerType

from .const import (
    ALWAYS_READ_ADDRESSES,
    CONF_PROTOCOL,
    CONF_REGISTERS,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_PROTOCOL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FEATURE_DEFAULTS,
    FEATURES,
    MAX_READ_BLOCK,
    PROTOCOL_TCP,
    PROTOCOL_UDP,
    SCHEDULE_DAY_ADDRESS,
    SCHEDULE_FIRST_ADDRESS,
    SCHEDULE_REGISTER_COUNT,
    RegisterDataType,
    feature_addresses,
    get_default_registers,
)

_LOGGER = logging.getLogger(__name__)


def _build_read_blocks(
    addresses: list[int], max_gap: int = 3, max_block: int = MAX_READ_BLOCK
) -> list[tuple[int, int]]:
    """Group sorted addresses into contiguous read blocks.

    Returns list of (start_address, count) tuples.
    Addresses within max_gap of each other are merged into one block, and no block
    grows past max_block registers - RS485 gateways in the field stop answering
    long reads, and a single unanswered read takes down every entity.
    """
    if not addresses:
        return []

    sorted_addrs = sorted(set(addresses))
    blocks: list[tuple[int, int]] = []
    block_start = sorted_addrs[0]
    block_end = sorted_addrs[0]

    for addr in sorted_addrs[1:]:
        if addr - block_end <= max_gap and addr - block_start + 1 <= max_block:
            block_end = addr
        else:
            blocks.append((block_start, block_end - block_start + 1))
            block_start = addr
            block_end = addr

    blocks.append((block_start, block_end - block_start + 1))
    return blocks


class WanasCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Coordinator to manage Modbus data fetching for Wanas."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host: str = entry.data[CONF_HOST]
        self.port: int = entry.data[CONF_PORT]
        self.slave_id: int = entry.data[CONF_SLAVE_ID]
        self.protocol: str = entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
        self._client: AsyncModbusTcpClient | AsyncModbusUdpClient | None = None
        # One RS485 bus behind a transparent gateway: every exchange, read or write,
        # has to be the only one in flight. RTU frames carry no transaction id, so
        # overlapping requests cannot be told apart on the way back.
        self._bus = asyncio.Lock()

        # Build effective register map: defaults overridden by user options
        defaults = get_default_registers()
        overrides = entry.options.get(CONF_REGISTERS, {})
        self.registers: dict[str, int | str] = {**defaults, **overrides}

        # Optional modules the unit does not have: options win over the original
        # answers from the config flow, so they can be corrected later.
        self.features: dict[str, bool] = {
            name: entry.options.get(name, entry.data.get(name, FEATURE_DEFAULTS[name]))
            for name in FEATURES
        }

        # Pre-compute read blocks from address keys only (skip *_name keys).
        # Registers belonging to a module the unit does not have are dropped, unless
        # another entity that is still present also reads them.
        skip: set[int] = set()
        for name, present in self.features.items():
            if not present:
                skip |= feature_addresses(name)
        keep = {
            v for k, v in self.registers.items()
            if k.endswith("_address") and isinstance(v, int)
        } - skip
        keep |= ALWAYS_READ_ADDRESSES
        self._read_blocks = _build_read_blocks(sorted(keep))

    @property
    def read_blocks(self) -> list[tuple[int, int]]:
        """The (start, count) requests this coordinator issues, for diagnostics."""
        return list(self._read_blocks)

    def has_feature(self, feature: str | None) -> bool:
        """Whether an entity's optional module is present. Untagged entities always are."""
        return feature is None or self.features.get(feature, True)

    def _create_client(self) -> AsyncModbusTcpClient | AsyncModbusUdpClient:
        """Create a Modbus client based on protocol selection."""
        if self.protocol == PROTOCOL_UDP:
            return AsyncModbusUdpClient(
                host=self.host, port=self.port, framer=FramerType.SOCKET
            )
        if self.protocol == PROTOCOL_TCP:
            return AsyncModbusTcpClient(
                host=self.host, port=self.port, framer=FramerType.SOCKET
            )
        # RTU over TCP
        return AsyncModbusTcpClient(
            host=self.host, port=self.port, framer=FramerType.RTU
        )

    def _drop_client(self) -> None:
        """Close and forget the client. Dropping it without closing leaks the socket."""
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 - closing must never mask the real error
                _LOGGER.debug("Ignoring error while closing the Modbus client", exc_info=True)

    async def _get_client(self) -> AsyncModbusTcpClient | AsyncModbusUdpClient:
        """Get or create the Modbus client."""
        if self._client is None or not self._client.connected:
            self._drop_client()
            self._client = self._create_client()
            connected = await self._client.connect()
            if not connected:
                self._drop_client()
                raise UpdateFailed(
                    f"Failed to connect to Modbus device at {self.host}:{self.port}"
                )
        return self._client

    async def _read_registers(
        self, client: AsyncModbusTcpClient | AsyncModbusUdpClient, address: int, count: int
    ) -> list[int]:
        """Read holding registers and return values."""
        result = await client.read_holding_registers(
            address=address, count=count, device_id=self.slave_id
        )
        if result.isError():
            raise UpdateFailed(
                f"Error reading registers at address {address}: {result}"
            )
        return result.registers

    async def _async_update_data(self) -> dict[int, int]:
        """Fetch data from Modbus device."""
        async with self._bus:
            try:
                client = await self._get_client()
            except UpdateFailed:
                raise
            except Exception as err:
                self._drop_client()
                raise UpdateFailed(f"Connection error: {err}") from err

            data: dict[int, int] = {}
            try:
                for start, count in self._read_blocks:
                    regs = await self._read_registers(client, start, count)
                    for i, val in enumerate(regs):
                        data[start + i] = val
            except UpdateFailed:
                raise
            except Exception as err:
                self._drop_client()
                raise UpdateFailed(f"Error fetching data: {err}") from err

        return data

    async def _write_locked(self, address: int, value: int) -> None:
        """Write one holding register. The caller must hold the bus lock."""
        try:
            client = await self._get_client()
            result = await client.write_register(
                address=address, value=value, device_id=self.slave_id
            )
        except Exception as err:
            self._drop_client()
            raise HomeAssistantError(
                f"Wanas: writing register {address} failed: {err}"
            ) from err

        if result.isError():
            # The device refused the write - a read-only register or a value out of
            # range. That is a bad request, not a broken connection, so the client
            # stays open and the user gets told what happened.
            raise HomeAssistantError(
                f"Wanas: device rejected the write of {value} to register {address}: {result}"
            )

    async def _read_locked(self, address: int, count: int) -> list[int]:
        """Read holding registers for a service call. The caller must hold the bus lock."""
        try:
            client = await self._get_client()
            result = await client.read_holding_registers(
                address=address, count=count, device_id=self.slave_id
            )
        except Exception as err:
            self._drop_client()
            raise HomeAssistantError(
                f"Wanas: reading registers {address}-{address + count - 1} failed: {err}"
            ) from err
        if result.isError():
            raise HomeAssistantError(
                f"Wanas: device rejected the read of registers {address}-{address + count - 1}: {result}"
            )
        return list(result.registers)

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a value to a holding register."""
        async with self._bus:
            await self._write_locked(address, value)

        # Show the new value at once instead of waiting out the refresh debounce,
        # then confirm it against the device on the next poll.
        if self.data is not None:
            self.async_set_updated_data({**self.data, address: value})
        await self.async_request_refresh()

    async def async_write_registers(self, values: dict[int, int]) -> None:
        """Write several registers in order as one exchange nothing else can interleave with."""
        async with self._bus:
            for address, value in values.items():
                await self._write_locked(address, value)

        if self.data is not None:
            self.async_set_updated_data({**self.data, **values})
        await self.async_request_refresh()

    async def async_read_week(self) -> dict[int, list[int]]:
        """Read the weekly program for every day, then put the day selector back.

        Registers 10-23 only show the day register 8 points at, so reading the week
        means stepping 8 through 0-6. The bus lock is held throughout: a poll or a
        write landing in between would see, or change, the wrong day.
        """
        week: dict[int, list[int]] = {}
        async with self._bus:
            (selected,) = await self._read_locked(SCHEDULE_DAY_ADDRESS, 1)
            try:
                for day in range(7):
                    await self._write_locked(SCHEDULE_DAY_ADDRESS, day)
                    week[day] = await self._read_locked(
                        SCHEDULE_FIRST_ADDRESS, SCHEDULE_REGISTER_COUNT
                    )
            finally:
                await self._write_locked(SCHEDULE_DAY_ADDRESS, selected)
        return week

    async def async_write_schedule(self, days: list[int], values: dict[int, int]) -> None:
        """Write program registers (10-23) for the given days, restoring the selector."""
        async with self._bus:
            (selected,) = await self._read_locked(SCHEDULE_DAY_ADDRESS, 1)
            try:
                for day in days:
                    await self._write_locked(SCHEDULE_DAY_ADDRESS, day)
                    for address, value in values.items():
                        await self._write_locked(address, value)
            finally:
                await self._write_locked(SCHEDULE_DAY_ADDRESS, selected)
        await self.async_request_refresh()

    async def async_close(self) -> None:
        """Close the Modbus client connection."""
        async with self._bus:
            self._drop_client()

    @staticmethod
    def get_sensor_value(
        data: dict[int, int], address: int, data_type: RegisterDataType, scale: float | None
    ) -> float | int | None:
        """Parse a register value with type and scale handling."""
        raw = data.get(address)
        if raw is None:
            return None

        if data_type == RegisterDataType.INT16:
            raw = ctypes.c_int16(raw).value

        if scale is not None:
            return round(raw * scale, 1)

        return raw
