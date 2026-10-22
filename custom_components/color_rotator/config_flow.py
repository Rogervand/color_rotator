"""Config flow: each entry is one rotation group."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN
from .settings import default_settings


class ColorRotatorConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input.get("name", "")).strip()
            if not name:
                errors["name"] = "required"
            elif any(e.title.lower() == name.lower() for e in self._async_current_entries()):
                errors["name"] = "already_exists"
            else:
                return self.async_create_entry(title=name, data={}, options=default_settings())
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("name"): str}),
            errors=errors,
        )
