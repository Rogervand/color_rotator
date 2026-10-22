"""Switch entity per rotation group: on = rotating."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE_UPDATED, VERSION
from .rotator import Rotator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([RotationSwitch(entry.runtime_data)])
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("next_color", None, "async_next_color")


class RotationSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_icon = "mdi:palette"

    def __init__(self, rotator: Rotator) -> None:
        self._rotator = rotator
        self._attr_unique_id = rotator.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, rotator.entry_id)},
            name=rotator.entry.title,
            manufacturer="Color Rotator",
            model="Rotation group",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_STATE_UPDATED.format(self._rotator.entry_id), self._update
            )
        )

    @callback
    def _update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._rotator.running

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st = self._rotator.status()
        st.pop("running", None)
        st.pop("applied", None)
        st["entry_id"] = self._rotator.entry_id
        st["entities"] = list(self._rotator.settings["entities"])
        st["color_count"] = len(self._rotator.settings["colors"])
        st["interval"] = self._rotator.settings["interval"]
        return st

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._rotator.async_start(manual=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._rotator.async_stop()

    async def async_next_color(self) -> None:
        await self._rotator.async_skip()
