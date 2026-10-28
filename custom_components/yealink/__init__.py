"""Yealink IP Phone integration (SIP-T31W and other T3x/T4x models)."""

from __future__ import annotations

import logging
from http import HTTPStatus

import voluptuous as vol
from aiohttp import web
from homeassistant.components import persistent_notification, webhook
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import YealinkClient
from .const import (
    ACTION_URL_EVENTS,
    ACTION_URL_VARIABLES,
    CONF_PASSWORD,
    CONF_POLL_STATUS,
    CONF_USERNAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
)
from .coordinator import YealinkCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.EVENT,
]

SERVICE_DIAL = "dial"
DIAL_SCHEMA = vol.Schema(
    {vol.Required("device_id"): cv.string, vol.Required("number"): cv.string}
)

type YealinkConfigEntry = ConfigEntry[YealinkCoordinator]


def webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    """Best-effort absolute URL of the webhook."""
    path = webhook.async_generate_path(webhook_id)
    base = hass.config.internal_url or "http://<IP_HOME_ASSISTANT>:8123"
    return f"{base}{path}"


def action_url_config(url: str) -> str:
    """Auto-provisioning lines for every event."""
    query = "&".join(f"{k}={v}" for k, v in ACTION_URL_VARIABLES.items())
    return "\n".join(
        f"action_url.{event} = {url}?event={event}&{query}"
        for event in ACTION_URL_EVENTS
    )


async def async_setup_entry(hass: HomeAssistant, entry: YealinkConfigEntry) -> bool:
    data = entry.data
    client = YealinkClient(
        async_get_clientsession(hass),
        data[CONF_HOST],
        data.get(CONF_USERNAME),
        data.get(CONF_PASSWORD),
    )
    coordinator = YealinkCoordinator(
        hass, entry.entry_id, client, data.get(CONF_POLL_STATUS, False)
    )
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, data[CONF_HOST])},
        manufacturer="Yealink",
        name=data[CONF_NAME],
        model=coordinator.state.model or "SIP-T31W",
        sw_version=coordinator.state.firmware,
        configuration_url=f"http://{data[CONF_HOST]}",
    )

    async def _handle(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        params = dict(request.query)
        if request.method == "POST":
            try:
                params.update(await request.post())
            except Exception:  # noqa: BLE001
                pass
        if "event" not in params:
            return web.Response(status=HTTPStatus.BAD_REQUEST)
        coordinator.async_handle_event(params)
        hass.bus.async_fire(
            f"{DOMAIN}_event", {"device": data[CONF_HOST], **params}
        )
        return web.Response(status=HTTPStatus.OK)

    webhook.async_register(
        hass,
        DOMAIN,
        f"Yealink {data[CONF_NAME]}",
        data[CONF_WEBHOOK_ID],
        _handle,
        allowed_methods=["GET", "POST"],
    )

    if not coordinator.state.last_event:
        url = webhook_url(hass, data[CONF_WEBHOOK_ID])
        persistent_notification.async_create(
            hass,
            "Dans l'interface web du téléphone: **Features > Action URL**, ou en "
            "auto-provisioning, ajoutez ces lignes (remplacez l'IP de Home "
            f"Assistant si besoin) :\n\n```\n{action_url_config(url)}\n```\n\n"
            "Autorisez aussi l'IP de Home Assistant dans **Security > Trusted IP > "
            "Action URI Allow IP List** pour le contrôle (boutons).",
            title=f"Yealink {data[CONF_NAME]} : configuration du téléphone",
            notification_id=f"{DOMAIN}_{entry.entry_id}",
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DIAL):

        async def _dial(call: ServiceCall) -> None:
            registry = dr.async_get(hass)
            device = registry.async_get(call.data["device_id"])
            if device is None:
                return
            for config_entry_id in device.config_entries:
                ent = hass.config_entries.async_get_entry(config_entry_id)
                if ent and ent.domain == DOMAIN and ent.state is ConfigEntryState.LOADED:
                    await ent.runtime_data.client.async_dial(call.data["number"])

        hass.services.async_register(DOMAIN, SERVICE_DIAL, _dial, schema=DIAL_SCHEMA)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: YealinkConfigEntry) -> bool:
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_save()
    return unloaded
