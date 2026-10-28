"""Do-not-disturb switch (state follows Action URL events)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YealinkConfigEntry
from .const import ACTION_URI_KEYS
from .entity import YealinkEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: YealinkConfigEntry, add: AddEntitiesCallback
) -> None:
    add([YealinkDnd(entry.runtime_data, entry)])


class YealinkDnd(YealinkEntity, SwitchEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "dnd_switch")

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.dnd

    async def async_turn_on(self, **kwargs: Any) -> None:
        if await self.coordinator.client.async_press_key(ACTION_URI_KEYS["dnd_on"]):
            self.coordinator.state.dnd = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if await self.coordinator.client.async_press_key(ACTION_URI_KEYS["dnd_off"]):
            self.coordinator.state.dnd = False
            self.async_write_ha_state()
