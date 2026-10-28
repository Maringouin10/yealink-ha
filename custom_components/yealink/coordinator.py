"""Coordinator: merges pushed Action URL events with periodic polling."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import YealinkClient
from .const import DOMAIN, POLL_INTERVAL_SECONDS, STORAGE_VERSION
from .parser import PhoneState

_LOGGER = logging.getLogger(__name__)


class YealinkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the phone state."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        client: YealinkClient,
        poll_status: bool,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        self.client = client
        self.poll_status = poll_status
        self.state = PhoneState()
        self.last_seen = None
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self._listeners: list = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if data:
            self.state.load(data)

    async def async_save(self) -> None:
        await self._store.async_save(self.state.to_dict())

    @callback
    def async_add_event_listener(self, cb) -> Any:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    @callback
    def async_handle_event(self, params: dict[str, Any]) -> None:
        """Called by the webhook for every Action URL event."""
        now = dt_util.now()
        self.state.apply(params, now)
        self.last_seen = now
        self._store.async_delay_save(self.state.to_dict, 10)
        data = dict(self.data or {})
        data["online"] = True
        self.async_set_updated_data(data)
        for cb in list(self._listeners):
            cb(self.state.last_event, params)

    async def _async_update_data(self) -> dict[str, Any]:
        online = await self.client.async_ping()
        status: dict[str, str] = {}
        if online:
            self.last_seen = dt_util.now()
            if self.poll_status:
                status = await self.client.async_get_status()
        return {"online": online, "status": status}
