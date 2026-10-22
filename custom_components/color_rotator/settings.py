"""Settings schema and helpers."""
from __future__ import annotations

import copy
import re

import voluptuous as vol

from .const import (
    DEFAULT_SETTINGS,
    END_LEAVE,
    END_OFF,
    END_RESTORE,
    MAX_INTERVAL,
    MAX_TRANSITION,
    MIN_INTERVAL,
    MODE_OFFSET,
    MODE_SYNC,
    ORDER_RANDOM,
    ORDER_SEQUENTIAL,
    TRIGGER_SUNRISE,
    TRIGGER_SUNSET,
    TRIGGER_TIME,
)

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


def _time_str(value):
    value = str(value)
    if not _TIME_RE.match(value):
        raise vol.Invalid("time must be HH:MM")
    hour, minute = value.split(":")
    return f"{int(hour):02d}:{minute}"


def _entity_id(value):
    value = str(value)
    if not value.startswith("light.") or len(value) < 7:
        raise vol.Invalid(f"{value} is not a light entity")
    return value


_PCT = vol.All(vol.Coerce(int), vol.Range(min=1, max=100))
_BYTE = vol.All(vol.Coerce(int), vol.Range(min=0, max=255))

COLOR_SCHEMA = vol.Schema(
    {
        vol.Required("rgb"): vol.All([_BYTE], vol.Length(min=3, max=3)),
        vol.Optional("name", default=""): vol.All(str, vol.Length(max=40)),
        vol.Optional("brightness", default=100): _PCT,
    }
)

TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required("type"): vol.In([TRIGGER_TIME, TRIGGER_SUNRISE, TRIGGER_SUNSET]),
        vol.Optional("time", default="00:00"): _time_str,
        vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=-720, max=720)),
    }
)

SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional("enabled", default=False): bool,
        vol.Optional("days", default=list(range(7))): vol.All(
            [vol.All(vol.Coerce(int), vol.Range(min=0, max=6))], vol.Unique()
        ),
        vol.Required("start"): TRIGGER_SCHEMA,
        vol.Required("end"): TRIGGER_SCHEMA,
    }
)

SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional("entities", default=list): vol.All([_entity_id], vol.Unique()),
        vol.Optional("colors", default=list): vol.All([COLOR_SCHEMA], vol.Length(max=64)),
        vol.Optional("global_brightness_enabled", default=False): bool,
        vol.Optional("global_brightness", default=100): _PCT,
        vol.Optional("order", default=ORDER_SEQUENTIAL): vol.In([ORDER_SEQUENTIAL, ORDER_RANDOM]),
        vol.Optional("avoid_repeat", default=True): bool,
        vol.Optional("mode", default=MODE_SYNC): vol.In([MODE_SYNC, MODE_OFFSET]),
        vol.Optional("interval", default=60): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_INTERVAL, max=MAX_INTERVAL)
        ),
        vol.Optional("transition", default=2): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=MAX_TRANSITION)
        ),
        vol.Optional("end_action", default=END_RESTORE): vol.In([END_RESTORE, END_OFF, END_LEAVE]),
        vol.Optional("schedule", default=lambda: copy.deepcopy(DEFAULT_SETTINGS["schedule"])): SCHEDULE_SCHEMA,
    },
    extra=vol.REMOVE_EXTRA,
)


def default_settings() -> dict:
    return copy.deepcopy(DEFAULT_SETTINGS)


def validate(settings: dict) -> dict:
    """Validate and normalise; raises vol.Invalid."""
    return SETTINGS_SCHEMA(copy.deepcopy(settings))


def merged(stored: dict | None) -> dict:
    """Stored options merged over defaults, tolerant of old/partial data."""
    base = default_settings()
    if stored:
        base.update(stored)
    try:
        return validate(base)
    except vol.Invalid:
        return validate(default_settings())
