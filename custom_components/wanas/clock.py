"""Encoding of the controller clock in registers 50 (date) and 51 (time)."""

from __future__ import annotations

from datetime import datetime, tzinfo


def encode_clock(moment: datetime) -> tuple[int, int]:
    """Return the (date, time) register values for a local datetime."""
    date_value = (moment.day << 11) | (moment.month << 7) | (moment.year - 2000)
    time_value = (moment.hour << 8) | moment.minute
    return date_value, time_value


def decode_clock(date_value: int, time_value: int, zone: tzinfo) -> datetime | None:
    """Return the controller's local datetime, or None if the registers are not a date.

    The unit keeps local wall time with no zone, so the caller passes the zone Home
    Assistant is configured for.
    """
    day = (date_value >> 11) & 0x1F
    month = (date_value >> 7) & 0x0F
    year = 2000 + (date_value & 0x7F)
    hour = (time_value >> 8) & 0xFF
    minute = time_value & 0xFF
    try:
        return datetime(year, month, day, hour, minute, tzinfo=zone)
    except ValueError:
        return None
