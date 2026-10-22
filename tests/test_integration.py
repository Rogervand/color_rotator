"""End-to-end tests inside a real Home Assistant instance."""
from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.color_rotator.const import DOMAIN
from custom_components.color_rotator.settings import default_settings

RGB = {"supported_color_modes": ["hs"], "friendly_name": "x"}


def _settings(**kw):
    s = default_settings()
    s.update(
        entities=["light.a", "light.b"],
        colors=[
            {"name": "red", "rgb": [255, 0, 0], "brightness": 100},
            {"name": "lime", "rgb": [0, 255, 0], "brightness": 50},
            {"name": "blue", "rgb": [0, 0, 255], "brightness": 25},
        ],
        interval=10,
        transition=0,
    )
    s.update(kw)
    return s


async def _setup(hass: HomeAssistant, **kw):
    hass.states.async_set(
        "light.a", "on", {**RGB, "color_mode": "hs", "hs_color": (30.0, 50.0), "brightness": 120}
    )
    hass.states.async_set("light.b", "off", RGB)
    entry = MockConfigEntry(domain=DOMAIN, title="Porch", data={}, options=_settings(**kw))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    return entry, on, off


def _by_entity(calls):
    out = {}
    for c in calls:
        for e in c.data["entity_id"] if isinstance(c.data["entity_id"], list) else [c.data["entity_id"]]:
            out[e] = c.data
    return out


async def test_sync_sequential_and_restore(hass: HomeAssistant):
    entry, on, off = await _setup(hass)
    assert hass.states.get("switch.porch").state == "off"

    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.porch"}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("switch.porch").state == "on"
    assert len(on) == 1
    assert on[0].data["entity_id"] == ["light.a", "light.b"]
    assert on[0].data["rgb_color"] == [255, 0, 0]
    assert on[0].data["brightness_pct"] == 100

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()
    assert on[-1].data["rgb_color"] == [0, 255, 0]
    assert on[-1].data["brightness_pct"] == 50

    attrs = hass.states.get("switch.porch").attributes
    assert attrs["current_color"]["name"] == "lime"

    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.porch"}, blocking=True)
    await hass.async_block_till_done()
    restored = on[-1].data
    assert restored["entity_id"] == "light.a"
    assert restored["hs_color"] == [30.0, 50.0] and restored["brightness"] == 120
    assert off[-1].data["entity_id"] == "light.b"
    assert hass.states.get("switch.porch").state == "off"


async def test_offset_and_global_brightness(hass: HomeAssistant):
    entry, on, off = await _setup(
        hass, mode="offset", global_brightness_enabled=True, global_brightness=40
    )
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.porch"}, blocking=True)
    await hass.async_block_till_done()
    by = _by_entity(on)
    assert by["light.a"]["rgb_color"] == [255, 0, 0]
    assert by["light.b"]["rgb_color"] == [0, 255, 0]
    assert by["light.a"]["brightness_pct"] == 40 and by["light.b"]["brightness_pct"] == 40


async def test_random_never_repeats(hass: HomeAssistant):
    entry, on, off = await _setup(hass, order="random", avoid_repeat=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.porch"}, blocking=True)
    await hass.async_block_till_done()
    for _ in range(30):
        await hass.services.async_call(DOMAIN, "next_color", {"entity_id": "switch.porch"}, blocking=True)
        await hass.async_block_till_done()
    seq = [tuple(c.data["rgb_color"]) for c in on]
    assert len(seq) == 31
    assert all(a != b for a, b in zip(seq, seq[1:]))
    assert len(set(seq)) == 3


async def test_end_action_off(hass: HomeAssistant):
    entry, on, off = await _setup(hass, end_action="off")
    rot = entry.runtime_data
    await rot.async_start()
    await rot.async_stop()
    await hass.async_block_till_done()
    assert off[-1].data["entity_id"] == ["light.a", "light.b"]


async def test_schedule_starts_and_stops(hass: HomeAssistant, freezer):
    tz = dt_util.get_default_time_zone()
    freezer.move_to(dt_util.as_utc(dt_util.now(tz).replace(hour=17, minute=59, second=0, microsecond=0)))
    sched = {
        "enabled": True,
        "days": list(range(7)),
        "start": {"type": "time", "time": "18:00", "offset": 0},
        "end": {"type": "time", "time": "18:05", "offset": 0},
    }
    entry, on, off = await _setup(hass, schedule=sched)
    assert hass.states.get("switch.porch").state == "off"

    freezer.tick(timedelta(minutes=1, seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("switch.porch").state == "on"

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("switch.porch").state == "off"
    assert hass.states.get("switch.porch").attributes["next_schedule_is_start"] is True


async def test_starts_when_loaded_inside_window(hass: HomeAssistant, freezer):
    tz = dt_util.get_default_time_zone()
    freezer.move_to(dt_util.as_utc(dt_util.now(tz).replace(hour=20, minute=0, second=0, microsecond=0)))
    sched = {
        "enabled": True,
        "days": list(range(7)),
        "start": {"type": "time", "time": "18:00", "offset": 0},
        "end": {"type": "time", "time": "02:00", "offset": 0},
    }
    await _setup(hass, schedule=sched)
    assert hass.states.get("switch.porch").state == "on"


async def test_websocket(hass: HomeAssistant, hass_ws_client):
    entry, on, off = await _setup(hass)
    ws = await hass_ws_client(hass)

    await ws.send_json({"id": 1, "type": f"{DOMAIN}/list"})
    res = await ws.receive_json()
    assert res["success"] and res["result"][0]["switch_entity_id"] == "switch.porch"

    new = _settings(interval=4)  # below minimum
    await ws.send_json({"id": 2, "type": f"{DOMAIN}/update", "entry_id": entry.entry_id, "settings": new})
    res = await ws.receive_json()
    assert not res["success"]

    new = _settings(interval=8 * 3600 + 1)  # above maximum
    await ws.send_json({"id": 3, "type": f"{DOMAIN}/update", "entry_id": entry.entry_id, "settings": new})
    assert not (await ws.receive_json())["success"]

    new = _settings(interval=30, entities=["light.a"])
    await ws.send_json({"id": 4, "type": f"{DOMAIN}/update", "entry_id": entry.entry_id, "settings": new})
    res = await ws.receive_json()
    assert res["success"] and res["result"]["settings"]["interval"] == 30
    assert entry.options["entities"] == ["light.a"]

    await ws.send_json({"id": 5, "type": f"{DOMAIN}/control", "entry_id": entry.entry_id, "action": "start"})
    res = await ws.receive_json()
    assert res["success"] and res["result"]["status"]["running"]
    await hass.async_block_till_done()
    assert on[-1].data["entity_id"] == ["light.a"]

    await ws.send_json({"id": 6, "type": f"{DOMAIN}/create", "name": "Kitchen"})
    res = await ws.receive_json()
    assert res["success"] and res["result"]["title"] == "Kitchen"
    await hass.async_block_till_done()
    assert hass.states.get("switch.kitchen") is not None

    await ws.send_json({"id": 7, "type": f"{DOMAIN}/create", "name": "kitchen"})
    assert not (await ws.receive_json())["success"]


async def test_entity_removed_while_running_is_restored(hass: HomeAssistant):
    entry, on, off = await _setup(hass)
    rot = entry.runtime_data
    await rot.async_start()
    await hass.async_block_till_done()
    await rot.async_update_settings({**rot.settings, "entities": ["light.b"]})
    await hass.async_block_till_done()
    restored = [c.data for c in on if c.data.get("entity_id") == "light.a"]
    assert restored and restored[-1]["hs_color"] == [30.0, 50.0]


async def test_config_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Deck"})
    assert result["type"] == "create_entry" and result["title"] == "Deck"
    await hass.async_block_till_done()


async def test_card_served(hass: HomeAssistant, hass_client):
    await _setup(hass)
    client = await hass_client()
    resp = await client.get("/color_rotator/color-rotator-card.js")
    assert resp.status == 200
    assert "color-rotator-card" in await resp.text()


async def test_dark_colors_become_dimmer_not_identical(hass: HomeAssistant):
    colors = [
        {"name": "maroon", "rgb": [128, 0, 0], "brightness": 100},
        {"name": "gray", "rgb": [128, 128, 128], "brightness": 80},
        {"name": "black", "rgb": [0, 0, 0], "brightness": 100},
    ]
    entry, on, off = await _setup(hass, colors=colors, global_brightness_enabled=False)
    rot = entry.runtime_data
    await rot.async_start()
    await hass.async_block_till_done()
    assert on[-1].data["rgb_color"] == [255, 0, 0] and on[-1].data["brightness_pct"] == 50
    await rot.async_skip()
    await hass.async_block_till_done()
    assert on[-1].data["rgb_color"] == [255, 255, 255] and on[-1].data["brightness_pct"] == 40
    n_off = len(off)
    await rot.async_skip()
    await hass.async_block_till_done()
    assert len(off) == n_off + 1
