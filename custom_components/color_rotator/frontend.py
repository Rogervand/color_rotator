"""Make the card available to dashboards, including during startup.

Home Assistant serves the frontend before custom integrations finish loading,
so a dashboard opened during startup would not see a module registered only
by this integration. To avoid that, the card is also copied to /config/www and
registered as a dashboard resource; both are available as soon as the frontend
starts on the next boot.
"""
from __future__ import annotations

import filecmp
import logging
import shutil
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL, DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

LOCAL_DIR = DOMAIN  # /config/www/color_rotator/
LOCAL_URL = f"/local/{LOCAL_DIR}/{CARD_FILENAME}"


def _copy_card(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or not filecmp.cmp(src, dest, shallow=False):
        shutil.copyfile(src, dest)


async def async_register_card(hass: HomeAssistant) -> None:
    src = Path(__file__).parent / "www" / CARD_FILENAME

    # 1. Served by this integration; covers the very first boot after install.
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(src), True)])
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")

    # 2. Copy to /config/www so /local serves it from the start of every later boot.
    dest = Path(hass.config.path("www")) / LOCAL_DIR / CARD_FILENAME
    try:
        await hass.async_add_executor_job(_copy_card, src, dest)
    except OSError as err:
        _LOGGER.warning("Could not copy card to %s: %s", dest, err)
        return

    # 3. Register as a dashboard resource (storage-mode dashboards only).
    await _async_ensure_resource(hass)


async def _async_ensure_resource(hass: HomeAssistant) -> None:
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or lovelace.resource_mode != "storage":
        _LOGGER.info(
            "Dashboards use YAML resources; add %s (type: module) to keep the card "
            "available during startup",
            LOCAL_URL,
        )
        return

    resources = lovelace.resources
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    url = f"{LOCAL_URL}?v={VERSION}"
    existing = [r for r in resources.async_items() if str(r.get("url", "")).split("?")[0] == LOCAL_URL]
    try:
        if not existing:
            await resources.async_create_item({"res_type": "module", "url": url})
        else:
            first, *dupes = existing
            if first.get("url") != url:
                await resources.async_update_item(first["id"], {"res_type": "module", "url": url})
            for dupe in dupes:
                await resources.async_delete_item(dupe["id"])
    except Exception:  # noqa: BLE001 - never block setup over a resource entry
        _LOGGER.exception("Could not register the Color Rotator card as a dashboard resource")
