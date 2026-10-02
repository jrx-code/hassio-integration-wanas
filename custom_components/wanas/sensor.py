"""Sensor platform for Wanas integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .clock import decode_clock
from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    CLOCK_DATE_ADDRESS,
    CLOCK_TIME_ADDRESS,
    SCHEDULE_DAY_ADDRESS,
    SCHEDULE_DAYS,
    SCHEDULE_FIRST_ADDRESS,
    SCHEDULE_REGISTER_COUNT,
    SENSOR_DESCRIPTIONS,
    WanasSensorDescription,
)
from .coordinator import WanasCoordinator
from .entity import device_info, device_key
from .recovery import Recovery, compute
from .schedule import DAY_MINUTES, day_periods, summary

# Read-only, values come from the coordinator.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wanas sensor entities."""
    coordinator: WanasCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        WanasSensor(coordinator, entry, desc)
        for desc in SENSOR_DESCRIPTIONS
        if coordinator.has_feature(desc.feature)
    ]
    entities.append(WanasClockSensor(coordinator, entry))
    entities.append(WanasScheduleSensor(coordinator, entry))
    entities.append(WanasCurrentPeriodSensor(coordinator, entry))
    entities.append(WanasRecoveryPowerSensor(coordinator, entry))
    entities.append(WanasRecoveryEfficiencySensor(coordinator, entry))
    entities.append(WanasRecoveredEnergySensor(coordinator, entry))
    async_add_entities(entities)


class WanasSensor(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """Representation of a Wanas sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WanasCoordinator,
        entry: ConfigEntry,
        description: WanasSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._description = description
        self._attr_unique_id = f"{device_key(entry)}_{description.key}"
        self._attr_translation_key = description.key
        # Setting _attr_name at all wins over translation_key in Entity._name_internal,
        # so only set it when the advanced register options carry a name the user
        # actually changed. Otherwise the translated name is used.
        name = coordinator.registers.get(f"{description.key}_name", description.name)
        if name != description.name:
            self._attr_name = name
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        address = self.coordinator.registers.get(
            f"{self._description.key}_address", self._description.address
        )
        return WanasCoordinator.get_sensor_value(
            self.coordinator.data,
            address,
            self._description.data_type,
            self._description.scale,
        )


class WanasClockSensor(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """The controller's own clock (registers 50 and 51), which the weekly program runs on.

    It drifts - minutes per week on the unit this was written against - and nothing
    sets it except the panel or the sync button, so it is worth being able to see.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "controller_clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the clock sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_controller_clock"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> datetime | None:
        """Return the controller time as an aware datetime."""
        data = self.coordinator.data
        if not data or CLOCK_DATE_ADDRESS not in data or CLOCK_TIME_ADDRESS not in data:
            return None
        return decode_clock(
            data[CLOCK_DATE_ADDRESS],
            data[CLOCK_TIME_ADDRESS],
            dt_util.get_default_time_zone(),
        )


class WanasScheduleSensor(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """The selected schedule day in one line, the way the panel's table reads.

    State: '00:00-06:00 I 18° | 06:00-07:00 II 20° | ...'. Attributes carry the day and
    the five periods with from, until, speed and temperature.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "schedule_summary"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the schedule sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_schedule_summary"
        self._attr_device_info = device_info(entry)

    def _periods(self) -> list[dict] | None:
        data = self.coordinator.data
        addresses = range(SCHEDULE_FIRST_ADDRESS, SCHEDULE_FIRST_ADDRESS + SCHEDULE_REGISTER_COUNT)
        if not data or any(address not in data for address in addresses):
            return None
        return day_periods([data[address] for address in addresses])

    @property
    def native_value(self) -> str | None:
        """Return the summary line."""
        periods = self._periods()
        return summary(periods) if periods else None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the selected day and its periods."""
        periods = self._periods()
        if not periods:
            return None
        day = (self.coordinator.data or {}).get(SCHEDULE_DAY_ADDRESS)
        return {
            "day": SCHEDULE_DAYS[day] if day is not None and 0 <= day < 7 else None,
            "periods": periods,
        }


class WanasCurrentPeriodSensor(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """Which schedule period the unit runs now, from today's program in the week cache.

    State: the period number, 1-5. Attributes: from, until, speed, temperature and the
    day. Unknown until the first week read has finished.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "current_period"

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the current period sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_key(entry)}_current_period"
        self._attr_device_info = device_info(entry)

    def _now(self) -> tuple[str, dict] | None:
        week = self.coordinator.week
        if not week:
            return None
        now = dt_util.now()
        day = (now.weekday() + 1) % 7  # 0 = Sunday, as register 8 counts
        program = week.get(day)
        if not program:
            return None
        periods = day_periods(program)
        minutes = now.hour * 60 + now.minute
        for number, period in enumerate(periods, start=1):
            start = _minutes(period["from"])
            end = DAY_MINUTES if number == len(periods) else _minutes(period["until"])
            if start <= minutes < end:
                return SCHEDULE_DAYS[day], {"number": number, **period}
        return None

    @property
    def native_value(self) -> int | None:
        """Return the period number."""
        now = self._now()
        return now[1]["number"] if now else None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the period's from, until, speed, temperature and the day."""
        now = self._now()
        if not now:
            return None
        day, period = now
        return {
            "day": day,
            "from": period["from"],
            "until": period["until"],
            "speed": period["speed"],
            "temperature": period["temperature"],
        }


# With any of these running, the supply temperature is no longer the exchanger's doing.
RECOVERY_BLOCKERS = ("bypass_state", "heater_state", "cooler_state", "gwc_state")

_SENSORS = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
_BINARY_SENSORS = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}


def current_recovery(coordinator: WanasCoordinator) -> Recovery | None:
    """Recovery from the last poll, or None when it is unknown or not happening."""
    data = coordinator.data
    if not data:
        return None
    for key in RECOVERY_BLOCKERS:
        desc = _BINARY_SENSORS[key]
        if not coordinator.has_feature(desc.feature):
            continue
        address = coordinator.registers.get(f"{key}_address", desc.address)
        state = data.get(address)
        if state is None or state != 0:
            return None

    def value(key: str) -> float | None:
        desc = _SENSORS[key]
        address = coordinator.registers.get(f"{key}_address", desc.address)
        return WanasCoordinator.get_sensor_value(data, address, desc.data_type, desc.scale)

    return compute(
        outdoor=value("outdoor_temperature"),
        supply=value("supply_temperature"),
        indoor=value("indoor_temperature"),
        supply_airflow=value("supply_airflow"),
        exhaust=value("exhaust_temperature"),
        exhaust_airflow=value("exhaust_airflow"),
    )


class _WanasRecoveryEntity(CoordinatorEntity[WanasCoordinator], SensorEntity):
    """Shared identity for the three heat recovery sensors."""

    _attr_has_entity_name = True
    _key: str

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the recovery sensor."""
        super().__init__(coordinator)
        self._attr_translation_key = self._key
        self._attr_unique_id = f"{device_key(entry)}_{self._key}"
        self._attr_device_info = device_info(entry)


class WanasRecoveryPowerSensor(_WanasRecoveryEntity):
    """Heat (or, in summer, cooling) the exchanger hands to the supply air, in W.

    Unknown with the bypass open or a heater, cooler or ground loop running.
    """

    _key = "heat_recovery_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    @property
    def native_value(self) -> float | None:
        """Return the recovered power."""
        recovery = current_recovery(self.coordinator)
        return recovery.power if recovery else None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the mode, the supply air temperature gain and the extract-side power."""
        recovery = current_recovery(self.coordinator)
        if not recovery:
            return None
        return {
            "mode": recovery.mode,
            "temperature_gain": recovery.delta,
            "extract_side_power": recovery.extract_power,
        }


class WanasRecoveryEfficiencySensor(_WanasRecoveryEntity):
    """Supply-side temperature ratio, (supply - outdoor) / (indoor - outdoor), in %."""

    _key = "heat_recovery_efficiency"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | None:
        """Return the efficiency."""
        recovery = current_recovery(self.coordinator)
        return recovery.efficiency if recovery else None


class WanasRecoveredEnergySensor(_WanasRecoveryEntity, RestoreSensor):
    """Recovered power integrated over time, in kWh, for statistics and the Energy dashboard.

    Integrated on every poll with the trapezoid rule. A gap longer than MAX_GAP (Home
    Assistant stopped, the unit unreachable) is skipped rather than bridged, and while
    recovery is not happening nothing is added.
    """

    _key = "heat_recovery_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    MAX_GAP = 600  # s

    def __init__(self, coordinator: WanasCoordinator, entry: ConfigEntry) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator, entry)
        self._total = 0.0
        self._last: tuple[datetime, float] | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the running total."""
        await super().async_added_to_hass()
        restored = await self.async_get_last_sensor_data()
        if restored is not None and isinstance(restored.native_value, (int, float)):
            self._total = float(restored.native_value)

    @callback
    def _handle_coordinator_update(self) -> None:
        recovery = current_recovery(self.coordinator) if self.coordinator.last_update_success else None
        now = dt_util.utcnow()
        if recovery is None:
            self._last = None
        else:
            if self._last is not None:
                since, power = self._last
                seconds = (now - since).total_seconds()
                if 0 < seconds <= self.MAX_GAP:
                    self._total += (power + recovery.power) / 2 * seconds / 3_600_000
            self._last = (now, recovery.power)
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        """Return the recovered energy."""
        return round(self._total, 3)


def _minutes(text: str) -> int:
    hours, _, minutes = text.partition(":")
    return int(hours) * 60 + int(minutes)
