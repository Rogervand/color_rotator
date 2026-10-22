"""Rotation engine: one Rotator per config entry (rotation group)."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_point_in_utc_time
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import dt as dt_util

from . import schedule as sched
from .const import (
    END_LEAVE,
    END_OFF,
    END_RESTORE,
    MODE_OFFSET,
    ORDER_RANDOM,
    SIGNAL_STATE_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .settings import merged

_LOGGER = logging.getLogger(__name__)

LIGHT = "light"

# color_mode -> attribute to replay when restoring
_RESTORE_ATTR = {
    "hs": "hs_color",
    "xy": "xy_color",
    "rgb": "rgb_color",
    "rgbw": "rgbw_color",
    "rgbww": "rgbww_color",
    "color_temp": "color_temp_kelvin",
}


class RuntimeStore:
    """Persists running flags and pre-rotation light snapshots across restarts."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, dict] = {}

    async def async_load(self) -> None:
        self.data = (await self._store.async_load()) or {}

    def get(self, entry_id: str) -> dict:
        return self.data.setdefault(entry_id, {"running": False, "manual": False, "snapshot": {}})

    @callback
    def save(self) -> None:
        self._store.async_delay_save(lambda: self.data, 1)

    @callback
    def remove(self, entry_id: str) -> None:
        self.data.pop(entry_id, None)
        self.save()


def snapshot_state(hass: HomeAssistant, entity_id: str) -> dict | None:
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    snap: dict[str, Any] = {"state": state.state}
    if state.state == STATE_ON:
        attrs = state.attributes
        if attrs.get("brightness") is not None:
            snap["brightness"] = attrs["brightness"]
        mode = attrs.get("color_mode")
        attr = _RESTORE_ATTR.get(mode)
        if attr and attrs.get(attr) is not None:
            value = attrs[attr]
            snap[attr] = list(value) if isinstance(value, (list, tuple)) else value
    return snap


async def async_restore_snapshot(hass: HomeAssistant, snapshot: dict, transition: float = 0) -> None:
    for entity_id, snap in snapshot.items():
        if hass.states.get(entity_id) is None:
            continue
        try:
            if snap.get("state") != STATE_ON:
                data: dict[str, Any] = {ATTR_ENTITY_ID: entity_id}
                if transition:
                    data["transition"] = transition
                await hass.services.async_call(LIGHT, "turn_off", data, blocking=False)
                continue
            data = {ATTR_ENTITY_ID: entity_id}
            for key in ("brightness", *_RESTORE_ATTR.values()):
                if key in snap:
                    data[key] = snap[key]
            if transition:
                data["transition"] = transition
            await hass.services.async_call(LIGHT, "turn_on", data, blocking=False)
        except Exception:  # noqa: BLE001 - one bad light must not block the rest
            _LOGGER.exception("Failed to restore %s", entity_id)


def _hex(rgb: list[int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


class Rotator:
    """Runs one rotation group."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runtime: RuntimeStore) -> None:
        self.hass = hass
        self.entry = entry
        self.runtime = runtime
        self.settings: dict = merged(dict(entry.options))
        self.running = False
        self.manual = False
        self.base_index = -1
        self.applied: dict[str, int] = {}  # entity_id -> color index currently shown
        self.next_change: datetime | None = None
        self.sched_state = sched.ScheduleState(False, None, False)
        self._sched_active: bool | None = None
        self._tick_unsub: CALLBACK_TYPE | None = None
        self._sched_unsub: CALLBACK_TYPE | None = None
        self._started_unsub: CALLBACK_TYPE | None = None
        self._ha_started = False
        self._rng = random.Random()

    # ----------------------------------------------------------------- lifecycle
    @property
    def entry_id(self) -> str:
        return self.entry.entry_id

    @property
    def _rt(self) -> dict:
        return self.runtime.get(self.entry_id)

    async def async_setup(self) -> None:
        self._started_unsub = async_at_started(self.hass, self._async_hass_started)

    async def _async_hass_started(self, _hass: HomeAssistant) -> None:
        self._ha_started = True
        state = self._evaluate_schedule()
        self._sched_active = state.active
        rt = self._rt
        if state.active:
            await self.async_start(manual=False)
        elif rt.get("running") and rt.get("manual"):
            await self.async_start(manual=True)
        elif rt.get("running") or rt.get("snapshot"):
            # Was running on the schedule but the window ended while HA was down
            await self.async_stop()
        self._schedule_next_event()
        self._notify()

    async def async_unload(self) -> None:
        """Stop timers but leave lights and the persisted running flag alone."""
        if self._ha_started:
            self._started_unsub = None  # already fired; nothing to remove
        for unsub in (self._tick_unsub, self._sched_unsub, self._started_unsub):
            if unsub:
                unsub()
        self._tick_unsub = self._sched_unsub = self._started_unsub = None

    # ----------------------------------------------------------------- control
    async def async_start(self, manual: bool = True) -> None:
        if self.running:
            if manual:
                self.manual = True
                self._persist()
            return
        self.running = True
        self.manual = manual
        self.base_index = -1
        self.applied = {}
        self._snapshot_missing(self.settings["entities"])
        self._persist()
        await self._async_tick()

    async def async_stop(self) -> None:
        self._cancel_tick()
        was_snapshot = dict(self._rt.get("snapshot", {}))
        self.running = False
        self.manual = False
        self.next_change = None
        self.applied = {}
        action = self.settings["end_action"]
        transition = self.settings["transition"]
        entities = self.settings["entities"]
        if action == END_RESTORE:
            await async_restore_snapshot(self.hass, was_snapshot, transition)
        elif action == END_OFF and entities:
            data: dict[str, Any] = {ATTR_ENTITY_ID: entities}
            if transition:
                data["transition"] = transition
            await self.hass.services.async_call(LIGHT, "turn_off", data, blocking=False)
        self._rt["snapshot"] = {}
        self._persist()
        self._notify()

    async def async_skip(self) -> None:
        """Advance to the next color now."""
        if self.running:
            self._cancel_tick()
            await self._async_tick()

    async def async_update_settings(self, new: dict) -> None:
        old_entities = set(self.settings["entities"])
        self.settings = new
        new_entities = set(new["entities"])

        if self.running:
            removed = old_entities - new_entities
            if removed:
                snap = self._rt.get("snapshot", {})
                restore = {e: snap.pop(e) for e in list(removed) if e in snap}
                if new["end_action"] == END_RESTORE and restore:
                    await async_restore_snapshot(self.hass, restore, new["transition"])
                elif new["end_action"] == END_OFF:
                    await self.hass.services.async_call(
                        LIGHT, "turn_off", {ATTR_ENTITY_ID: sorted(removed)}, blocking=False
                    )
            self._snapshot_missing(new["entities"])
            self._persist()

        # Schedule may have changed; only act if the active state flipped
        state = self._evaluate_schedule()
        if self._ha_started:
            await self._apply_schedule_transition(state.active)
            self._schedule_next_event()

        if self.running:
            self._cancel_tick()
            if self.base_index >= len(new["colors"]):
                self.base_index = -1
            await self._async_tick()
        self._notify()

    # ----------------------------------------------------------------- rotation
    def _pick_base(self, n: int) -> int:
        if self.settings["order"] == ORDER_RANDOM:
            if n == 1:
                return 0
            choices = list(range(n))
            if self.settings["avoid_repeat"] and 0 <= self.base_index < n:
                choices.remove(self.base_index)
            return self._rng.choice(choices)
        return (self.base_index + 1) % n

    def _available_entities(self) -> list[str]:
        out = []
        for entity_id in self.settings["entities"]:
            st = self.hass.states.get(entity_id)
            if st is not None and st.state != STATE_UNAVAILABLE:
                out.append(entity_id)
        return out

    async def _async_tick(self, _now: datetime | None = None) -> None:
        self._tick_unsub = None
        if not self.running:
            return
        colors = self.settings["colors"]
        entities = self._available_entities()
        if colors and entities:
            n = len(colors)
            self.base_index = self._pick_base(n)
            step = 1 if self.settings["mode"] == MODE_OFFSET else 0
            groups: dict[int, list[str]] = {}
            for i, entity_id in enumerate(entities):
                idx = (self.base_index + i * step) % n
                groups.setdefault(idx, []).append(entity_id)
                self.applied[entity_id] = idx
            for idx, ids in groups.items():
                await self._async_apply(colors[idx], ids)

        interval = self.settings["interval"]
        self.next_change = dt_util.utcnow() + timedelta(seconds=interval)
        self._tick_unsub = async_call_later(self.hass, interval, self._async_tick_cb)
        self._notify()

    @callback
    def _async_tick_cb(self, now: datetime) -> None:
        self.hass.async_create_task(self._async_tick(now), eager_start=True)

    async def _async_apply(self, color: dict, entity_ids: list[str]) -> None:
        brightness = (
            self.settings["global_brightness"]
            if self.settings["global_brightness_enabled"]
            else color.get("brightness", 100)
        )
        data: dict[str, Any] = {
            ATTR_ENTITY_ID: entity_ids,
            "rgb_color": list(color["rgb"]),
            "brightness_pct": brightness,
        }
        if self.settings["transition"]:
            data["transition"] = self.settings["transition"]
        try:
            await self.hass.services.async_call(LIGHT, "turn_on", data, blocking=False)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to set %s on %s", color, entity_ids)

    def _cancel_tick(self) -> None:
        if self._tick_unsub:
            self._tick_unsub()
            self._tick_unsub = None

    # ----------------------------------------------------------------- schedule
    def _sun(self, event: str, day) -> datetime | None:
        return get_astral_event_date(self.hass, event, day)

    def _evaluate_schedule(self) -> sched.ScheduleState:
        self.sched_state = sched.evaluate(
            self.settings["schedule"], dt_util.utcnow(), dt_util.get_default_time_zone(), self._sun
        )
        return self.sched_state

    async def _apply_schedule_transition(self, active: bool) -> None:
        previous = self._sched_active
        self._sched_active = active
        if previous is None or previous == active:
            return
        if active and not self.running:
            await self.async_start(manual=False)
        elif not active and self.running:
            await self.async_stop()

    def _schedule_next_event(self) -> None:
        if self._sched_unsub:
            self._sched_unsub()
            self._sched_unsub = None
        event = self.sched_state.next_event
        if event is None:
            return
        self._sched_unsub = async_track_point_in_utc_time(
            self.hass, self._async_sched_cb, event + timedelta(seconds=1)
        )

    @callback
    def _async_sched_cb(self, _now: datetime) -> None:
        self._sched_unsub = None
        self.hass.async_create_task(self._async_sched_fired(), eager_start=True)

    async def _async_sched_fired(self) -> None:
        state = self._evaluate_schedule()
        await self._apply_schedule_transition(state.active)
        self._schedule_next_event()
        self._notify()

    # ----------------------------------------------------------------- helpers
    def _snapshot_missing(self, entity_ids: list[str]) -> None:
        snap = self._rt.setdefault("snapshot", {})
        for entity_id in entity_ids:
            if entity_id not in snap:
                value = snapshot_state(self.hass, entity_id)
                if value is not None:
                    snap[entity_id] = value

    def _persist(self) -> None:
        rt = self._rt
        rt["running"] = self.running
        rt["manual"] = self.manual
        self.runtime.save()

    @callback
    def _notify(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_STATE_UPDATED.format(self.entry_id))

    def status(self) -> dict:
        colors = self.settings["colors"]
        current = None
        if self.running and 0 <= self.base_index < len(colors):
            c = colors[self.base_index]
            current = {"index": self.base_index, "name": c.get("name", ""), "hex": _hex(c["rgb"])}
        ss = self.sched_state
        return {
            "running": self.running,
            "manual": self.manual,
            "current_color": current,
            "applied": {e: i for e, i in self.applied.items()},
            "next_change": self.next_change.isoformat() if self.next_change and self.running else None,
            "schedule_enabled": self.settings["schedule"]["enabled"],
            "schedule_active": ss.active,
            "next_schedule_event": ss.next_event.isoformat() if ss.next_event else None,
            "next_schedule_is_start": ss.next_is_start,
        }
