"""Minimal HTTP client for a Yealink phone (Action URI + optional web status)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import aiohttp

_LOGGER = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=6)

# Candidate key names (lower-case, substring match) in the web status payload.
STATUS_CANDIDATES: dict[str, tuple[str, ...]] = {
    "firmware": ("firmware", "softwareversion", "software_version"),
    "hardware": ("hardware",),
    "mac": ("macaddress", "mac"),
    "ip": ("ipv4", "ipaddress", "ip"),
    "uptime": ("uptime", "runtime"),
    "model": ("productname", "model"),
}


def _flatten(data: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            out.update(_flatten(value, f"{prefix}{key}".lower() + "."))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            out.update(_flatten(value, f"{prefix}{idx}."))
    elif data not in (None, ""):
        out[prefix.rstrip(".")] = str(data)
    return out


def extract_status(payload: Any) -> dict[str, str]:
    """Pick well-known fields from an unknown JSON layout, best effort."""
    flat = _flatten(payload)
    result: dict[str, str] = {}
    for target, needles in STATUS_CANDIDATES.items():
        for needle in needles:
            hit = next(
                (v for k, v in flat.items() if k.rsplit(".", 1)[-1].endswith(needle)),
                None,
            )
            if hit:
                result[target] = hit
                break
    return result


class YealinkClient:
    """Talks to the phone's built-in web server."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._session = session
        self.host = host
        self._username = username
        self._password = password
        self._base = f"http://{host}"

    async def async_ping(self) -> bool:
        """Return True if the phone's web server answers at all."""
        try:
            async with self._session.get(self._base, timeout=TIMEOUT) as resp:
                return resp.status < 500
        except (aiohttp.ClientError, TimeoutError):
            return False

    async def async_action_uri(self, query: str) -> bool:
        """Call /servlet?<query>; the phone must trust this host (Action URI)."""
        try:
            async with self._session.get(
                f"{self._base}/servlet?{query}", timeout=TIMEOUT
            ) as resp:
                if resp.status >= 400:
                    _LOGGER.warning(
                        "Phone %s rejected action %s (HTTP %s); check "
                        "Security > Trusted IP > Action URI allowed IP list",
                        self.host,
                        query,
                        resp.status,
                    )
                    return False
                return True
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("Action %s on %s failed: %s", query, self.host, err)
            return False

    async def async_press_key(self, key: str) -> bool:
        return await self.async_action_uri(f"key={quote(key)}")

    async def async_dial(self, number: str) -> bool:
        return await self.async_action_uri(f"key=number={quote(number)}")

    async def async_get_status(self) -> dict[str, str]:
        """EXPERIMENTAL: log in to the web UI and read the status page.

        The web UI endpoints are undocumented and vary with the firmware; any
        failure simply returns an empty dict.
        """
        if not self._username:
            return {}
        try:
            async with self._session.post(
                f"{self._base}/servlet?m=mod_listener&p=login&q=login",
                data={"username": self._username, "pwd": self._password or ""},
                timeout=TIMEOUT,
            ):
                pass
            async with self._session.get(
                f"{self._base}/servlet?m=mod_data&p=status&q=load", timeout=TIMEOUT
            ) as resp:
                if resp.status != 200:
                    return {}
                payload = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return {}
        return extract_status(payload)
