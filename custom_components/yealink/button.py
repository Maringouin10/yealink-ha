"""Buttons that press phone keys through Action URI."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YealinkConfigEntry
from .const import ACTION_URI_KEYS
from .entity import YealinkEntity

SKIP = {"dnd_on", "dnd_off"}  # handled by the DND switch


async def async_setup_entry(
    hass: HomeAssistant, entry: YealinkConfigEntry, add: AddEntitiesCallback
) -> None:
    add(
        YealinkButton(entry.runtime_data, entry, name, key)
        for name, key in ACTION_URI_KEYS.items()
        if name not in SKIP
    )


class YealinkButton(YealinkEntity, ButtonEntity):
    def __init__(self, coordinator, entry, name: str, key: str) -> None:
        super().__init__(coordinator, entry, f"btn_{name}")
        self._key = key
        if name == "reboot":
            self._attr_device_class = ButtonDeviceClass.RESTART

    async def async_press(self) -> None:
        await self.coordinator.client.async_press_key(self._key)
