"""Color Rotator: rotate lights through color lists on a schedule."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_FILENAME, CARD_URL, DOMAIN, VERSION
from .rotator import Rotator, RuntimeStore, async_restore_snapshot
from .websocket_api import async_register_websocket

PLATFORMS = [Platform.SWITCH]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def _async_domain_data(hass: HomeAssistant) -> dict:
    if DOMAIN not in hass.data:
        runtime = RuntimeStore(hass)
        await runtime.async_load()
        hass.data[DOMAIN] = {"runtime": runtime, "rotators": {}}
    return hass.data[DOMAIN]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await _async_domain_data(hass)
    card = Path(__file__).parent / "www" / CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), True)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = await _async_domain_data(hass)
    rotator = Rotator(hass, entry, data["runtime"])
    data["rotators"][entry.entry_id] = rotator
    entry.runtime_data = rotator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await rotator.async_setup()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        rotator: Rotator = hass.data[DOMAIN]["rotators"].pop(entry.entry_id)
        await rotator.async_unload()
    return ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Group deleted: put its lights back the way they were, then forget it."""
    data = await _async_domain_data(hass)
    runtime: RuntimeStore = data["runtime"]
    snap = runtime.data.get(entry.entry_id, {}).get("snapshot") or {}
    if snap:
        await async_restore_snapshot(hass, snap)
    runtime.remove(entry.entry_id)
