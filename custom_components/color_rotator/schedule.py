"""Pure schedule logic (no Home Assistant imports, so it is easy to test)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from .const import TRIGGER_SUNRISE, TRIGGER_SUNSET, TRIGGER_TIME

# sun_fn(event, day) -> aware datetime of "sunrise"/"sunset" on that local day, or None
SunFn = Callable[[str, date], "datetime | None"]


@dataclass
class ScheduleState:
    """Result of evaluating a schedule at a moment in time."""

    active: bool
    next_event: datetime | None
    next_is_start: bool
    window_end: datetime | None = None


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")[:2]
    return time(int(hour), int(minute))


def resolve_trigger(trigger: dict, day: date, tz: tzinfo, sun_fn: SunFn) -> datetime | None:
    """Resolve a start/end trigger to an aware datetime on the given local day."""
    kind = trigger.get("type", TRIGGER_TIME)
    offset = timedelta(minutes=int(trigger.get("offset", 0) or 0))
    if kind == TRIGGER_TIME:
        base = datetime.combine(day, _parse_time(trigger.get("time", "00:00")), tz)
        return base  # offset is ignored for fixed times
    if kind in (TRIGGER_SUNRISE, TRIGGER_SUNSET):
        event = sun_fn(kind, day)
        if event is None:  # polar day/night
            return None
        return event.astimezone(tz) + offset
    raise ValueError(f"Unknown trigger type {kind}")


def window_for(schedule: dict, day: date, tz: tzinfo, sun_fn: SunFn) -> tuple[datetime, datetime] | None:
    """Return the (start, end) window that starts on `day`, or None."""
    if day.weekday() not in schedule.get("days", []):
        return None
    start = resolve_trigger(schedule["start"], day, tz, sun_fn)
    if start is None:
        return None
    end = resolve_trigger(schedule["end"], day, tz, sun_fn)
    if end is not None and end <= start:
        # Window crosses midnight: the end belongs to the following day
        end = resolve_trigger(schedule["end"], day + timedelta(days=1), tz, sun_fn)
    if end is None or end <= start:
        return None
    return start, end


def evaluate(schedule: dict, now: datetime, tz: tzinfo, sun_fn: SunFn) -> ScheduleState:
    """Is the schedule active right now, and when is the next start/end?"""
    if not schedule.get("enabled") or not schedule.get("days"):
        return ScheduleState(False, None, False)

    today = now.astimezone(tz).date()

    # Active window? A window may have started yesterday and crossed midnight.
    for offset in (-1, 0):
        win = window_for(schedule, today + timedelta(days=offset), tz, sun_fn)
        if win and win[0] <= now < win[1]:
            return ScheduleState(True, win[1], False, win[1])

    # Next start within the coming week (+1 for safety)
    for offset in range(0, 9):
        win = window_for(schedule, today + timedelta(days=offset), tz, sun_fn)
        if win and win[0] > now:
            return ScheduleState(False, win[0], True)

    return ScheduleState(False, None, False)
