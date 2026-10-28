"""Sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YealinkConfigEntry, webhook_url
from .coordinator import YealinkCoordinator
from .entity import YealinkEntity
from .parser import IDLE, ON_HOLD, RINGING, DIALING, TALKING



@dataclass(frozen=True, kw_only=True)
class YealinkSensorDescription(SensorEntityDescription):
    value_fn: Callable[[YealinkCoordinator], Any]


def _s(c: YealinkCoordinator, name: str) -> Any:
    return getattr(c.state, name)


def _status(c: YealinkCoordinator, key: str) -> Any:
    return ((c.data or {}).get("status") or {}).get(key)


def _attr(key: str, **kw) -> YealinkSensorDescription:
    return YealinkSensorDescription(
        key=key, translation_key=key, value_fn=lambda c, k=key: _s(c, k), **kw
    )


DIAG = EntityCategory.DIAGNOSTIC
TS = SensorDeviceClass.TIMESTAMP
SECS = dict(
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
)
COUNT = dict(state_class=SensorStateClass.TOTAL_INCREASING)

SENSORS: tuple[YealinkSensorDescription, ...] = (
    YealinkSensorDescription(
        key="call_state",
        translation_key="call_state",
        device_class=SensorDeviceClass.ENUM,
        options=[IDLE, RINGING, DIALING, TALKING, ON_HOLD],
        value_fn=lambda c: c.state.call_state,
    ),
    YealinkSensorDescription(
        key="registration",
        translation_key="registration",
        device_class=SensorDeviceClass.ENUM,
        options=["registered", "unregistered", "failed"],
        value_fn=lambda c: c.state.registration,
    ),
    _attr("direction"),
    _attr("remote_number"),
    _attr("remote_name"),
    _attr("local_number"),
    _attr("call_id", entity_category=DIAG, entity_registry_enabled_default=False),
    _attr("call_started", device_class=TS),
    _attr("last_incoming_number"),
    _attr("last_incoming_name"),
    _attr("last_outgoing_number"),
    _attr("last_missed_number"),
    _attr("last_call_number"),
    _attr("last_call_direction"),
    _attr("last_call_duration", **SECS),
    _attr("last_call_time", device_class=TS),
    _attr("incoming_today", **COUNT),
    _attr("outgoing_today", **COUNT),
    _attr("missed_today", **COUNT),
    _attr("incoming_total", entity_category=DIAG, **COUNT),
    _attr("outgoing_total", entity_category=DIAG, **COUNT),
    _attr("answered_total", entity_category=DIAG, **COUNT),
    _attr("missed_total", entity_category=DIAG, **COUNT),
    _attr("talk_seconds_today", **SECS),
    _attr("total_talk_seconds", entity_category=DIAG, **SECS),
    _attr("active_user", entity_category=DIAG),
    _attr("active_host", entity_category=DIAG),
    _attr("last_event", entity_category=DIAG),
    _attr("last_event_time", device_class=TS, entity_category=DIAG),
    _attr("last_boot", device_class=TS, entity_category=DIAG),
    _attr("last_ip_change", device_class=TS, entity_category=DIAG),
    YealinkSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=TS,
        entity_category=DIAG,
        value_fn=lambda c: c.last_seen,
    ),
    YealinkSensorDescription(
        key="ip",
        translation_key="ip",
        entity_category=DIAG,
        value_fn=lambda c: c.state.ip or _status(c, "ip"),
    ),
    YealinkSensorDescription(
        key="mac",
        translation_key="mac",
        entity_category=DIAG,
        value_fn=lambda c: c.state.mac or _status(c, "mac"),
    ),
    YealinkSensorDescription(
        key="model",
        translation_key="model",
        entity_category=DIAG,
        value_fn=lambda c: c.state.model or _status(c, "model"),
    ),
    YealinkSensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=DIAG,
        value_fn=lambda c: c.state.firmware or _status(c, "firmware"),
    ),
    YealinkSensorDescription(
        key="hardware",
        translation_key="hardware",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _status(c, "hardware"),
    ),
    YealinkSensorDescription(
        key="uptime",
        translation_key="uptime",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _status(c, "uptime"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: YealinkConfigEntry, add: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        YealinkSensor(coordinator, entry, d) for d in SENSORS
    ]
    entities.append(YealinkWebhookSensor(coordinator, entry, hass))
    add(entities)


class YealinkSensor(YealinkEntity, SensorEntity):
    entity_description: YealinkSensorDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)


class YealinkWebhookSensor(YealinkEntity, SensorEntity):
    """Shows the Action URL to configure on the phone."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, hass) -> None:
        super().__init__(coordinator, entry, "webhook")
        self._url = webhook_url(hass, entry.data["webhook_id"])

    @property
    def native_value(self) -> str:
        return self._url
