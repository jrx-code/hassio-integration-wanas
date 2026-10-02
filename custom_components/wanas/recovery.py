"""Heat recovery of the exchanger, computed from the temperatures and airflow already read.

Supply side, as EN 308 defines the temperature ratio: what the outdoor air gained (or, in
summer, lost) on its way through the core, against what it could have gained. The supply
side also picks up the supply fan's motor heat, so it reads higher than the extract side;
the extract-side power is returned too, so the gap can be seen rather than hidden.
"""

from __future__ import annotations

from dataclasses import dataclass

# Air at about 20 °C: density 1.2 kg/m³ times specific heat 1005 J/(kg·K), per hour.
# W per (m³/h · K).
AIR_HEAT_CAPACITY = 1.2 * 1005 / 3600

# Below this indoor-outdoor difference the ratio is mostly sensor noise.
MIN_EFFICIENCY_DELTA = 2.0

# Plausible range of a working sensor. A faulty one reports 63066, which reads as -247.0 °C.
MIN_VALID_TEMPERATURE = -40.0
MAX_VALID_TEMPERATURE = 80.0

MODE_HEATING = "heating"
MODE_COOLING = "cooling"


@dataclass(frozen=True)
class Recovery:
    """What the exchanger does right now."""

    power: float  # W, always >= 0
    efficiency: float | None  # %, 0-100, None when indoor and outdoor are too close
    mode: str  # heating or cooling
    delta: float  # K the supply air gained (heating) or lost (cooling)
    extract_power: float | None  # W from the extract side, None without its readings


def _valid(value: float | None) -> bool:
    return value is not None and MIN_VALID_TEMPERATURE <= value <= MAX_VALID_TEMPERATURE


def compute(
    outdoor: float | None,
    supply: float | None,
    indoor: float | None,
    supply_airflow: float | None,
    exhaust: float | None = None,
    exhaust_airflow: float | None = None,
) -> Recovery | None:
    """Recovered power and efficiency, or None when the readings do not allow it.

    The caller decides whether recovery is meaningful at all: with the bypass open or a
    heater, cooler or ground loop running, the supply temperature no longer measures the
    exchanger alone.
    """
    if not (_valid(outdoor) and _valid(supply) and _valid(indoor)) or supply_airflow is None:
        return None
    assert outdoor is not None and supply is not None and indoor is not None
    drive = indoor - outdoor
    mode = MODE_HEATING if drive >= 0 else MODE_COOLING
    sign = 1 if mode == MODE_HEATING else -1
    # Only a change in the direction the indoor air pulls counts as recovery. Supply air a
    # little warmer than a warmer outdoor is fan heat, not recovered cooling.
    delta = max(0.0, sign * (supply - outdoor))
    power = AIR_HEAT_CAPACITY * max(0.0, supply_airflow) * delta

    efficiency = None
    if abs(drive) >= MIN_EFFICIENCY_DELTA:
        efficiency = max(0.0, min(100.0, 100 * (supply - outdoor) / drive))

    extract_power = None
    if _valid(exhaust) and exhaust_airflow is not None:
        assert exhaust is not None
        extract_power = AIR_HEAT_CAPACITY * max(0.0, exhaust_airflow) * max(
            0.0, sign * (indoor - exhaust)
        )

    return Recovery(
        power=round(power),
        efficiency=None if efficiency is None else round(efficiency),
        mode=mode,
        delta=round(delta, 1),
        extract_power=None if extract_power is None else round(extract_power),
    )
