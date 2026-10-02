"""Constants for the Wanas integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

DOMAIN = "wanas"

DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600

# Longest run of registers read in one request. RS485-to-Ethernet gateways stop
# answering beyond a certain block size, and one unanswered read makes the whole
# coordinator update fail, so keep requests short.
MAX_READ_BLOCK = 16

# Hard deadline for one bus call (connect, read or write). pymodbus gives up on its own
# after timeout x (retries + 1) = 12 s by default, so this only fires when a call never
# returns at all. Without it, one such call holds the bus lock forever and every poll and
# write after it queues up: the core modbus YAML hub stopped exactly like that, silently,
# on the unit this was written against.
BUS_TIMEOUT = 30

# Failed polls in a row after which the socket is dropped and opened afresh, whatever
# the failure was. Error responses alone keep the connection otherwise.
MAX_FAILED_POLLS = 3

# Weekly schedule ("Harmonogram tygodniowy", "Programy" on the panel): five periods per
# day. Register 8 does not report the current weekday: it selects which day registers
# 10-23 show and accept (0 = Sunday ... 6 = Saturday). Verified on a Combo 430 on
# 2026-10-02: writing period 1 on Saturday left Sunday and Friday as they were.
# 10-13 are where periods 1-4 end (minutes after midnight, each also the start of the
# next period), 14-18 the period fan speeds, 19-23 the period setpoints. The manual's
# register table says "strefa" (zone), but the manual uses that word for the building's
# day/night zone control (registers 58-70), so this code says "period".
SCHEDULE_DAY_ADDRESS = 8
SCHEDULE_FIRST_ADDRESS = 10
SCHEDULE_REGISTER_COUNT = 14
SCHEDULE_PERIOD_UNTIL_ADDRESSES = (10, 11, 12, 13)
SCHEDULE_PERIOD_SPEED_ADDRESSES = (14, 15, 16, 17, 18)
SCHEDULE_PERIOD_TEMPERATURE_ADDRESSES = (19, 20, 21, 22, 23)
SCHEDULE_DAYS = (
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
)

# Controller clock. Date is day<<11 | month<<7 | (year - 2000), as in the DTR. Time
# is hour<<8 | minute: the DTR example says hour<<7, the unit itself does not.
CLOCK_DATE_ADDRESS = 50
CLOCK_TIME_ADDRESS = 51

# Read on every poll whatever the register options say: the schedule day selector,
# the period boundaries (time entities) and the clock have fixed addresses and are
# not remappable.
ALWAYS_READ_ADDRESSES: frozenset[int] = frozenset(
    {
        SCHEDULE_DAY_ADDRESS,
        *SCHEDULE_PERIOD_UNTIL_ADDRESSES,
        CLOCK_DATE_ADDRESS,
        CLOCK_TIME_ADDRESS,
    }
)

# Entities of earlier releases that no longer exist, by platform and description key.
# Zone 1-4 end were minute numbers; the period boundaries are time entities now.
RETIRED_ENTITIES: tuple[tuple[str, str], ...] = (
    ("number", "zone_1_end"),
    ("number", "zone_2_end"),
    ("number", "zone_3_end"),
    ("number", "zone_4_end"),
)

# Day counters on registers 41 and 42 run to 180 days (DTR Combo 430/630, 04.2026).
MAX_MODULE_DAYS = 180

# Registers 52-54 are "Moc/Przepływ": percent of fan power, or the airflow in m³/h when
# the unit runs in constant-flow mode. The manufacturer table says 1-100 %, but the unit
# this was written against holds 100/200/400 in flow mode, so the range follows the
# airflow ceiling of register 0 and no unit is claimed.
MAX_FAN_SETPOINT = 1600

CONF_SCAN_INTERVAL = "scan_interval"
CONF_SLAVE_ID = "slave_id"
CONF_HAS_HEATER = "has_heater"
CONF_HAS_COOLER = "has_cooler"
CONF_HAS_HUMIDIFIER = "has_humidifier"
CONF_HAS_MAXICONTROL = "has_maxicontrol"
CONF_PROTOCOL = "protocol"
CONF_REGISTERS = "registers"
CONF_SHOW_ADVANCED = "show_advanced"
CONF_CONFIGURE_REGISTERS = "configure_registers"

# Optional modules. A unit without one of these still answers on the matching
# registers, so absence cannot be probed - it has to be declared by the user.
FEATURE_HEATER = CONF_HAS_HEATER
FEATURE_COOLER = CONF_HAS_COOLER
FEATURE_HUMIDIFIER = CONF_HAS_HUMIDIFIER
FEATURE_MAXICONTROL = CONF_HAS_MAXICONTROL
FEATURES: tuple[str, ...] = (
    FEATURE_HEATER,
    FEATURE_COOLER,
    FEATURE_HUMIDIFIER,
    FEATURE_MAXICONTROL,
)
# Heater, cooler and humidifier default to present, as they were before the question
# existed. maxiCONTROL room panels are an add-on, so entries created before it was
# asked about must not suddenly grow six entities.
FEATURE_DEFAULTS: dict[str, bool] = {
    FEATURE_HEATER: True,
    FEATURE_COOLER: True,
    FEATURE_HUMIDIFIER: True,
    FEATURE_MAXICONTROL: False,
}

PROTOCOL_RTU_OVER_TCP = "rtu_over_tcp"
PROTOCOL_TCP = "tcp"
PROTOCOL_UDP = "udp"
DEFAULT_PROTOCOL = PROTOCOL_RTU_OVER_TCP

PROTOCOL_OPTIONS = [
    PROTOCOL_RTU_OVER_TCP,
    PROTOCOL_TCP,
    PROTOCOL_UDP,
]


class RegisterDataType(IntEnum):
    """Data type for register values."""

    UINT16 = 0
    INT16 = 1


@dataclass(frozen=True)
class WanasSensorDescription:
    """Describes a Wanas sensor."""

    key: str
    name: str
    address: int
    data_type: RegisterDataType = RegisterDataType.UINT16
    scale: float | None = None
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    feature: str | None = None
    entity_category: EntityCategory | None = None


@dataclass(frozen=True)
class WanasBinarySensorDescription:
    """Describes a Wanas binary sensor."""

    key: str
    name: str
    address: int
    device_class: BinarySensorDeviceClass | None = None
    feature: str | None = None
    entity_category: EntityCategory | None = None


@dataclass(frozen=True)
class WanasSwitchDescription:
    """Describes a Wanas switch."""

    key: str
    name: str
    write_address: int
    verify_address: int
    on_value: int = 1
    off_value: int = 0
    feature: str | None = None
    entity_category: EntityCategory | None = None


@dataclass(frozen=True)
class WanasNumberDescription:
    """Describes a Wanas number entity."""

    key: str
    name: str
    write_address: int
    verify_address: int
    min_value: float = 0
    max_value: float = 255
    step: float = 1
    unit: str | None = None
    feature: str | None = None
    entity_category: EntityCategory | None = None


SENSOR_DESCRIPTIONS: tuple[WanasSensorDescription, ...] = (
    WanasSensorDescription(
        key="supply_airflow",
        name="Supply Airflow",
        address=0,
        unit=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="exhaust_airflow",
        name="Exhaust Airflow",
        address=1,
        unit=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="supply_fan_speed",
        name="Supply Fan Speed",
        address=2,
    ),
    WanasSensorDescription(
        key="exhaust_fan_speed",
        name="Exhaust Fan Speed",
        address=3,
    ),
    WanasSensorDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        address=4,
        data_type=RegisterDataType.INT16,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="exhaust_temperature",
        name="Exhaust Temperature",
        address=5,
        data_type=RegisterDataType.INT16,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="supply_temperature",
        name="Supply Temperature",
        address=6,
        data_type=RegisterDataType.INT16,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="indoor_temperature",
        name="Indoor Temperature",
        address=7,
        data_type=RegisterDataType.INT16,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="current_temperature",
        name="Current Temperature",
        address=29,
        data_type=RegisterDataType.INT16,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WanasSensorDescription(
        key="filter_replacement",
        name="Filter Replacement",
        address=36,
        unit=UnitOfTime.DAYS,
    ),
    WanasSensorDescription(
        key="system_errors",
        name="System Errors",
        address=37,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # maxiCONTROL room panels. Addresses and scaling come from a user's working
    # Modbus YAML (GitHub issue #1); the manufacturer table in config/hardware stops
    # at register 54, so these are not confirmed against it.
    WanasSensorDescription(
        key="room_temperature",
        name="Room Temperature",
        address=65,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        feature=FEATURE_MAXICONTROL,
    ),
    WanasSensorDescription(
        key="bathroom_1_temperature",
        name="Bathroom 1 Temperature",
        address=66,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        feature=FEATURE_MAXICONTROL,
    ),
    WanasSensorDescription(
        key="bathroom_2_temperature",
        name="Bathroom 2 Temperature",
        address=67,
        scale=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        feature=FEATURE_MAXICONTROL,
    ),
    WanasSensorDescription(
        key="room_humidity",
        name="Room Humidity",
        address=55,
        scale=0.1,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        feature=FEATURE_MAXICONTROL,
    ),
    WanasSensorDescription(
        key="bathroom_1_humidity",
        name="Bathroom 1 Humidity",
        address=56,
        scale=0.1,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        feature=FEATURE_MAXICONTROL,
    ),
    WanasSensorDescription(
        key="bathroom_2_humidity",
        name="Bathroom 2 Humidity",
        address=57,
        scale=0.1,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        feature=FEATURE_MAXICONTROL,
    ),
)

BINARY_SENSOR_DESCRIPTIONS: tuple[WanasBinarySensorDescription, ...] = (
    WanasBinarySensorDescription(
        key="gwc_state",
        name="GWC State",
        address=30,
    ),
    WanasBinarySensorDescription(
        key="bypass_state",
        name="Bypass State",
        address=31,
    ),
    WanasBinarySensorDescription(
        key="humidifier_state",
        name="Humidifier State",
        address=32,
        feature=FEATURE_HUMIDIFIER,
    ),
    WanasBinarySensorDescription(
        key="heater_state",
        name="Heater State",
        address=33,
        feature=FEATURE_HEATER,
    ),
    WanasBinarySensorDescription(
        key="cooler_state",
        name="Cooler State",
        address=34,
        feature=FEATURE_COOLER,
    ),
    WanasBinarySensorDescription(
        key="vacation_mode",
        name="Vacation Mode",
        address=35,
    ),
    # Registers 46-49 are read-only digital inputs on the controller. They report
    # the state of the external contacts wired to the unit, they are not setpoints.
    WanasBinarySensorDescription(
        key="input_speed_1",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Speed 1 Input",
        address=46,
    ),
    WanasBinarySensorDescription(
        key="input_speed_3",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Speed 3 Input",
        address=47,
    ),
    WanasBinarySensorDescription(
        key="input_hood",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Hood Input",
        address=48,
    ),
    WanasBinarySensorDescription(
        key="input_fire_alarm",
        name="Fire Alarm Input",
        address=49,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

SWITCH_DESCRIPTIONS: tuple[WanasSwitchDescription, ...] = (
    WanasSwitchDescription(
        key="gwc",
        name="GWC",
        write_address=38,
        verify_address=30,
    ),
    WanasSwitchDescription(
        key="bypass",
        name="Bypass",
        write_address=39,
        verify_address=31,
    ),
    WanasSwitchDescription(
        key="humidifier",
        name="Humidifier",
        write_address=40,
        verify_address=32,
        feature=FEATURE_HUMIDIFIER,
    ),
    WanasSwitchDescription(
        key="heater",
        name="Heater",
        write_address=41,
        verify_address=33,
        feature=FEATURE_HEATER,
    ),
    # Registers 41 and 42 are day counters (0-180) rather than booleans, but writing
    # 1 arms them for a day, which is how the unit has always been driven here. The
    # matching WanasNumber entities expose the full day range.
    WanasSwitchDescription(
        key="cooler",
        name="Cooler",
        write_address=42,
        verify_address=34,
        feature=FEATURE_COOLER,
    ),
    # One-tap versions of the timed functions: on writes the longest duration the
    # register allows, off writes 0. Fireplace and party count down in the register
    # itself, so "on" means "still running"; vacation reports through register 35.
    # The matching numbers set any other duration.
    WanasSwitchDescription(
        key="vacation_switch",
        name="Vacation Switch",
        write_address=43,
        verify_address=35,
        on_value=30,
    ),
    WanasSwitchDescription(
        key="fireplace_switch",
        name="Fireplace Switch",
        write_address=44,
        verify_address=44,
        on_value=180,
    ),
    WanasSwitchDescription(
        key="party_switch",
        name="Party Switch",
        write_address=45,
        verify_address=45,
        on_value=720,
    ),
)

NUMBER_DESCRIPTIONS: tuple[WanasNumberDescription, ...] = (
    WanasNumberDescription(
        key="heater_days",
        name="Heater Days",
        write_address=41,
        verify_address=41,
        min_value=0,
        max_value=MAX_MODULE_DAYS,
        step=1,
        unit=UnitOfTime.DAYS,
        feature=FEATURE_HEATER,
    ),
    WanasNumberDescription(
        key="cooler_days",
        name="Cooler Days",
        write_address=42,
        verify_address=42,
        min_value=0,
        max_value=MAX_MODULE_DAYS,
        step=1,
        unit=UnitOfTime.DAYS,
        feature=FEATURE_COOLER,
    ),
    WanasNumberDescription(
        key="vacation",
        name="Vacation",
        write_address=43,
        verify_address=43,
        min_value=0,
        max_value=30,
        step=1,
        unit=UnitOfTime.DAYS,
    ),
    WanasNumberDescription(
        key="fireplace",
        name="Fireplace",
        write_address=44,
        verify_address=44,
        min_value=0,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
    ),
    WanasNumberDescription(
        key="party",
        name="Party",
        write_address=45,
        verify_address=45,
        min_value=0,
        max_value=720,
        step=1,
        unit=UnitOfTime.MINUTES,
    ),
    # Registers 52-54 are the actual fan power setpoints. Registers 46-47, which an
    # earlier revision used here, are read-only digital inputs and are exposed as
    # binary sensors instead.
    WanasNumberDescription(
        key="zone_1_speed",
        name="Zone 1 Fan Speed",
        write_address=14,
        verify_address=14,
        min_value=0,
        max_value=3,
        step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_2_speed",
        name="Zone 2 Fan Speed",
        write_address=15,
        verify_address=15,
        min_value=0,
        max_value=3,
        step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_3_speed",
        name="Zone 3 Fan Speed",
        write_address=16,
        verify_address=16,
        min_value=0,
        max_value=3,
        step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_4_speed",
        name="Zone 4 Fan Speed",
        write_address=17,
        verify_address=17,
        min_value=0,
        max_value=3,
        step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_5_speed",
        name="Zone 5 Fan Speed",
        write_address=18,
        verify_address=18,
        min_value=0,
        max_value=3,
        step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_1_temperature",
        name="Zone 1 Temperature",
        write_address=19,
        verify_address=19,
        min_value=10,
        max_value=30,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_2_temperature",
        name="Zone 2 Temperature",
        write_address=20,
        verify_address=20,
        min_value=10,
        max_value=30,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_3_temperature",
        name="Zone 3 Temperature",
        write_address=21,
        verify_address=21,
        min_value=10,
        max_value=30,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_4_temperature",
        name="Zone 4 Temperature",
        write_address=22,
        verify_address=22,
        min_value=10,
        max_value=30,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="zone_5_temperature",
        name="Zone 5 Temperature",
        write_address=23,
        verify_address=23,
        min_value=10,
        max_value=30,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.CONFIG,
    ),
    WanasNumberDescription(
        key="fan_power_1",
        name="Fan Power 1",
        write_address=52,
        verify_address=52,
        min_value=1,
        max_value=MAX_FAN_SETPOINT,
        step=1,
    ),
    WanasNumberDescription(
        key="fan_power_2",
        name="Fan Power 2",
        write_address=53,
        verify_address=53,
        min_value=1,
        max_value=MAX_FAN_SETPOINT,
        step=1,
    ),
    WanasNumberDescription(
        key="fan_power_3",
        name="Fan Power 3",
        write_address=54,
        verify_address=54,
        min_value=1,
        max_value=MAX_FAN_SETPOINT,
        step=1,
    ),
)

def get_default_registers() -> dict[str, int]:
    """Build default register address mapping from descriptions."""
    regs: dict[str, int] = {}
    for desc in SENSOR_DESCRIPTIONS:
        regs[f"{desc.key}_address"] = desc.address
    for desc in BINARY_SENSOR_DESCRIPTIONS:
        regs[f"{desc.key}_address"] = desc.address
    for desc in SWITCH_DESCRIPTIONS:
        regs[f"{desc.key}_write_address"] = desc.write_address
        regs[f"{desc.key}_verify_address"] = desc.verify_address
    for desc in NUMBER_DESCRIPTIONS:
        regs[f"{desc.key}_write_address"] = desc.write_address
        regs[f"{desc.key}_verify_address"] = desc.verify_address
    return regs


def get_default_register_config() -> dict[str, int | str]:
    """Build default register config with names and addresses."""
    regs: dict[str, int | str] = {}
    for desc in SENSOR_DESCRIPTIONS:
        regs[f"{desc.key}_name"] = desc.name
        regs[f"{desc.key}_address"] = desc.address
    for desc in BINARY_SENSOR_DESCRIPTIONS:
        regs[f"{desc.key}_name"] = desc.name
        regs[f"{desc.key}_address"] = desc.address
    for desc in SWITCH_DESCRIPTIONS:
        regs[f"{desc.key}_name"] = desc.name
        regs[f"{desc.key}_write_address"] = desc.write_address
        regs[f"{desc.key}_verify_address"] = desc.verify_address
    for desc in NUMBER_DESCRIPTIONS:
        regs[f"{desc.key}_name"] = desc.name
        regs[f"{desc.key}_write_address"] = desc.write_address
        regs[f"{desc.key}_verify_address"] = desc.verify_address
    return regs


def feature_addresses(feature: str) -> set[int]:
    """Registers that exist only because of one optional module."""
    addrs: set[int] = set()
    for desc in (*SENSOR_DESCRIPTIONS, *BINARY_SENSOR_DESCRIPTIONS):
        if desc.feature == feature:
            addrs.add(desc.address)
    for desc in (*SWITCH_DESCRIPTIONS, *NUMBER_DESCRIPTIONS):
        if desc.feature == feature:
            addrs.update((desc.write_address, desc.verify_address))
    return addrs
