"""Config flow for Yealink IP Phone."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import webhook

from .api import YealinkClient
from .const import (
    CONF_PASSWORD,
    CONF_POLL_STATUS,
    CONF_USERNAME,
    CONF_WEBHOOK_ID,
    DEFAULT_NAME,
    DEFAULT_USERNAME,
    DOMAIN,
)


class YealinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = YealinkClient(
                async_get_clientsession(self.hass), user_input[CONF_HOST]
            )
            host = client.host
            self._async_abort_entries_match({CONF_HOST: host})
            if await client.async_ping():
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_HOST: host,
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_USERNAME: user_input.get(CONF_USERNAME) or None,
                        CONF_PASSWORD: user_input.get(CONF_PASSWORD) or None,
                        CONF_POLL_STATUS: user_input[CONF_POLL_STATUS],
                        CONF_WEBHOOK_ID: webhook.async_generate_id(),
                    },
                )
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
                vol.Required(CONF_POLL_STATUS, default=False): bool,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
