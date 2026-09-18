"""Constants for the Wanas integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

DOMAIN = "wanas"

DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

CONF_SLAVE_ID = "slave_id"
CONF_PROTOCOL = "protocol"
CONF_REGISTERS = "registers"
CONF_SHOW_ADVANCED = "show_advanced"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CONFIGURE_REGISTERS = "configure_registers"

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


@dataclass(frozen=True)
class WanasBinarySensorDescription:
    """Describes a Wanas binary sensor."""

    key: str
    name: str
    address: int
    device_class: BinarySensorDeviceClass | None = None


@dataclass(frozen=True)
class WanasSwitchDescription:
    """Describes a Wanas switch."""

    key: str
    name: str
    write_address: int
    verify_address: int
    on_value: int = 1
    off_value: int = 0


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
    ),
    WanasBinarySensorDescription(
        key="heater_state",
        name="Heater State",
        address=33,
    ),
    WanasBinarySensorDescription(
        key="cooler_state",
        name="Cooler State",
        address=34,
    ),
    WanasBinarySensorDescription(
        key="vacation_mode",
        name="Vacation Mode",
        address=35,
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
    ),
    WanasSwitchDescription(
        key="heater",
        name="Heater",
        write_address=41,
        verify_address=33,
    ),
    WanasSwitchDescription(
        key="cooler",
        name="Cooler",
        write_address=42,
        verify_address=34,
    ),
    WanasSwitchDescription(
        key="hood",
        name="Hood",
        write_address=48,
        verify_address=48,
    ),
)

NUMBER_DESCRIPTIONS: tuple[WanasNumberDescription, ...] = (
    WanasNumberDescription(
        key="vacation",
        name="Vacation",
        write_address=43,
        verify_address=35,
        min_value=0,
        max_value=255,
        step=1,
        unit=UnitOfTime.DAYS,
    ),
    WanasNumberDescription(
        key="fireplace",
        name="Fireplace",
        write_address=44,
        verify_address=44,
        min_value=0,
        max_value=240,
        step=1,
        unit=UnitOfTime.MINUTES,
    ),
    WanasNumberDescription(
        key="party",
        name="Party",
        write_address=45,
        verify_address=45,
        min_value=0,
        max_value=240,
        step=1,
        unit=UnitOfTime.MINUTES,
    ),
    WanasNumberDescription(
        key="fan_speed_1",
        name="Fan Speed 1",
        write_address=46,
        verify_address=46,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
    ),
    WanasNumberDescription(
        key="fan_speed_3",
        name="Fan Speed 3",
        write_address=47,
        verify_address=47,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
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
