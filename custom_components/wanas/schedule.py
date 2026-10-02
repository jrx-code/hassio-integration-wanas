"""The weekly schedule as the unit's panel shows it: five periods per day.

The panel ("Programy") lists each day as five rows - from, until, fan speed, temperature.
Period 1 starts at 00:00 and period 5 ends at 00:00; the four boundaries in between are
registers 10-13, each the end of one period and the start of the next.
"""

from __future__ import annotations

from typing import Any

from .const import (
    SCHEDULE_FIRST_ADDRESS,
    SCHEDULE_PERIOD_SPEED_ADDRESSES,
    SCHEDULE_PERIOD_TEMPERATURE_ADDRESSES,
    SCHEDULE_PERIOD_UNTIL_ADDRESSES,
)

PERIOD_COUNT = 5
DAY_MINUTES = 1440
BOUNDARY_MIN = 15
BOUNDARY_MAX = 1425
BOUNDARY_STEP = 15

SPEED_LABELS = ("0", "I", "II", "III")


def format_minutes(minutes: int) -> str:
    """Minutes after midnight as HH:MM; 1440 is shown as 00:00, like on the panel."""
    minutes %= DAY_MINUTES
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def boundary_error(minutes: int) -> str | None:
    """Why a period boundary cannot be stored, or None if it can."""
    if minutes % BOUNDARY_STEP:
        return f"{format_minutes(minutes)} is not on a quarter hour"
    if not BOUNDARY_MIN <= minutes <= BOUNDARY_MAX:
        return f"{format_minutes(minutes)} is outside 00:15-23:45"
    return None


def order_error(boundaries: list[int]) -> str | None:
    """Why four boundaries are not a valid day, or None if they are."""
    for index in range(1, len(boundaries)):
        if boundaries[index] <= boundaries[index - 1]:
            return (
                f"period {index + 1} would end at {format_minutes(boundaries[index])}, "
                f"not after period {index}, which ends at "
                f"{format_minutes(boundaries[index - 1])}"
            )
    return None


def bounds(data: dict[int, int], period: int) -> tuple[int, int] | None:
    """(from, until) in minutes of one period (1-5) of the selected day."""
    ends = [data.get(address) for address in SCHEDULE_PERIOD_UNTIL_ADDRESSES]
    start = 0 if period == 1 else ends[period - 2]
    end = DAY_MINUTES if period == PERIOD_COUNT else ends[period - 1]
    if start is None or end is None:
        return None
    return start, end


def day_periods(values: list[int]) -> list[dict[str, Any]]:
    """The five periods of one day from its 14 program registers (10-23)."""

    def reg(address: int) -> int:
        return values[address - SCHEDULE_FIRST_ADDRESS]

    ends = [reg(address) for address in SCHEDULE_PERIOD_UNTIL_ADDRESSES]
    starts = [0, *ends]
    ends = [*ends, DAY_MINUTES]
    return [
        {
            "from": format_minutes(starts[index]),
            "until": format_minutes(ends[index]),
            "speed": reg(SCHEDULE_PERIOD_SPEED_ADDRESSES[index]),
            "temperature": reg(SCHEDULE_PERIOD_TEMPERATURE_ADDRESSES[index]),
        }
        for index in range(PERIOD_COUNT)
    ]


def summary(periods: list[dict[str, Any]]) -> str:
    """One line per day, e.g. '00:00-06:00 I 18° | 06:00-07:00 II 20° | ...'."""
    parts = []
    for period in periods:
        speed = period["speed"]
        label = SPEED_LABELS[speed] if 0 <= speed < len(SPEED_LABELS) else str(speed)
        parts.append(f"{period['from']}-{period['until']} {label} {period['temperature']}°")
    return " | ".join(parts)
