"""Websocket commands used by the card."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .settings import validate


def _rotators(hass: HomeAssistant) -> dict:
    return hass.data.get(DOMAIN, {}).get("rotators", {})


def _switch_entity(hass: HomeAssistant, entry_id: str) -> str | None:
    reg = er.async_get(hass)
    return reg.async_get_entity_id("switch", DOMAIN, entry_id)


def _describe(hass: HomeAssistant, rotator) -> dict[str, Any]:
    return {
        "entry_id": rotator.entry_id,
        "title": rotator.entry.title,
        "switch_entity_id": _switch_entity(hass, rotator.entry_id),
        "settings": rotator.settings,
        "status": rotator.status(),
    }


def _get(hass, connection, msg):
    rotator = _rotators(hass).get(msg["entry_id"])
    if rotator is None:
        connection.send_error(msg["id"], "not_found", "Rotation group not found (is it loaded?)")
    return rotator


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    for handler in (ws_list, ws_get, ws_update, ws_control, ws_create):
        websocket_api.async_register_command(hass, handler)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list"})
@callback
def ws_list(hass: HomeAssistant, connection, msg) -> None:
    connection.send_result(
        msg["id"],
        sorted(
            (_describe(hass, r) for r in _rotators(hass).values()),
            key=lambda g: g["title"].lower(),
        ),
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/get", vol.Required("entry_id"): str}
)
@callback
def ws_get(hass: HomeAssistant, connection, msg) -> None:
    if rotator := _get(hass, connection, msg):
        connection.send_result(msg["id"], _describe(hass, rotator))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/update",
        vol.Required("entry_id"): str,
        vol.Required("settings"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_update(hass: HomeAssistant, connection, msg) -> None:
    rotator = _get(hass, connection, msg)
    if rotator is None:
        return
    try:
        settings = validate(msg["settings"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    # Write options without triggering a reload; the rotator applies changes live.
    hass.config_entries.async_update_entry(rotator.entry, options=settings)
    await rotator.async_update_settings(settings)
    connection.send_result(msg["id"], _describe(hass, rotator))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/control",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In(["start", "stop", "skip"]),
    }
)
@websocket_api.async_response
async def ws_control(hass: HomeAssistant, connection, msg) -> None:
    rotator = _get(hass, connection, msg)
    if rotator is None:
        return
    action = msg["action"]
    if action == "start":
        await rotator.async_start(manual=True)
    elif action == "stop":
        await rotator.async_stop()
    else:
        await rotator.async_skip()
    connection.send_result(msg["id"], _describe(hass, rotator))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/create", vol.Required("name"): vol.All(str, vol.Length(min=1, max=60))}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_create(hass: HomeAssistant, connection, msg) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"name": msg["name"]}
    )
    entry = result.get("result")
    if result.get("type") != "create_entry" or entry is None:
        connection.send_error(msg["id"], "create_failed", str(result.get("reason") or result.get("errors")))
        return
    rotator = _rotators(hass).get(entry.entry_id)
    if rotator is None:
        connection.send_error(msg["id"], "create_failed", "Group created but did not load")
        return
    connection.send_result(msg["id"], _describe(hass, rotator))
