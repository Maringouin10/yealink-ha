"""Binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YealinkConfigEntry
from .coordinator import YealinkCoordinator
from .entity import YealinkEntity
from .parser import IDLE, RINGING


@dataclass(frozen=True, kw_only=True)
class YealinkBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[YealinkCoordinator], bool | None]


def _flag(key: str, **kw) -> YealinkBinaryDescription:
    return YealinkBinaryDescription(
        key=key, translation_key=key, value_fn=lambda c, k=key: getattr(c.state, k), **kw
    )


BINARY_SENSORS: tuple[YealinkBinaryDescription, ...] = (
    YealinkBinaryDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda c: (c.data or {}).get("online"),
    ),
    YealinkBinaryDescription(
        key="registered",
        translation_key="registered",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda c: (
            None if c.state.registration is None else c.state.registration == "registered"
        ),
    ),
    YealinkBinaryDescription(
        key="ringing",
        translation_key="ringing",
        device_class=BinarySensorDeviceClass.SOUND,
        value_fn=lambda c: c.state.call_state == RINGING,
    ),
    YealinkBinaryDescription(
        key="in_call",
        translation_key="in_call",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda c: c.state.call_state != IDLE,
    ),
    _flag("hook_off", device_class=BinarySensorDeviceClass.OPENING),
    _flag("muted"),
    _flag("on_hold"),
    _flag("dnd"),
    _flag("forward_always"),
    _flag("forward_busy"),
    _flag("forward_no_answer"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: YealinkConfigEntry, add: AddEntitiesCallback
) -> None:
    add(YealinkBinary(entry.runtime_data, entry, d) for d in BINARY_SENSORS)


class YealinkBinary(YealinkEntity, BinarySensorEntity):
    entity_description: YealinkBinaryDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator)
