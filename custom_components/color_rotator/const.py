"""Constants for Color Rotator."""
from __future__ import annotations

DOMAIN = "color_rotator"
VERSION = "1.0.1"

CARD_FILENAME = "color-rotator-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.snapshots"

SIGNAL_STATE_UPDATED = f"{DOMAIN}_state_updated_{{}}"

# Interval limits (seconds)
MIN_INTERVAL = 5
MAX_INTERVAL = 8 * 60 * 60
MAX_TRANSITION = 300

ORDER_SEQUENTIAL = "sequential"
ORDER_RANDOM = "random"

MODE_SYNC = "sync"
MODE_OFFSET = "offset"

END_RESTORE = "restore"
END_OFF = "off"
END_LEAVE = "leave"

TRIGGER_TIME = "time"
TRIGGER_SUNRISE = "sunrise"
TRIGGER_SUNSET = "sunset"

# Color modes that can take an rgb_color
RGB_CAPABLE_MODES = {"hs", "xy", "rgb", "rgbw", "rgbww"}

DEFAULT_SETTINGS: dict = {
    "entities": [],
    "colors": [
        {"name": "red", "rgb": [255, 0, 0], "brightness": 100},
        {"name": "lime", "rgb": [0, 255, 0], "brightness": 100},
        {"name": "blue", "rgb": [0, 0, 255], "brightness": 100},
    ],
    "global_brightness_enabled": False,
    "global_brightness": 100,
    "order": ORDER_SEQUENTIAL,
    "avoid_repeat": True,
    "mode": MODE_SYNC,
    "interval": 60,
    "transition": 2,
    "end_action": END_RESTORE,
    "schedule": {
        "enabled": False,
        "days": [0, 1, 2, 3, 4, 5, 6],
        "start": {"type": TRIGGER_SUNSET, "time": "18:00", "offset": 0},
        "end": {"type": TRIGGER_TIME, "time": "23:00", "offset": 0},
    },
}
