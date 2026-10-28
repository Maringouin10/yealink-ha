"""Event entity for automations (one event type per Action URL event)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YealinkConfigEntry
from .const import ACTION_URL_EVENTS
from .entity import YealinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: YealinkConfigEntry, add: AddEntitiesCallback
) -> None:
    add([YealinkPhoneEvent(entry.runtime_data, entry)])


class YealinkPhoneEvent(YealinkEntity, EventEntity):
    _attr_event_types = list(ACTION_URL_EVENTS)

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "phone_event")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_event_listener(self._on_event)
        )

    @callback
    def _on_event(self, event: str | None, params: dict[str, Any]) -> None:
        if event in self._attr_event_types:
            attrs = {k: v for k, v in params.items() if k != "event" and not str(v).startswith("$")}
            self._trigger_event(event, attrs)
            self.async_write_ha_state()
