"""Base entity."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YealinkCoordinator


class YealinkEntity(CoordinatorEntity[YealinkCoordinator]):
    """Entity attached to the phone device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: YealinkCoordinator, entry, key: str) -> None:
        super().__init__(coordinator)
        host = entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            manufacturer="Yealink",
            name=entry.data[CONF_NAME],
        )

    @property
    def available(self) -> bool:
        # Pushed state stays meaningful even if a poll fails.
        return True
