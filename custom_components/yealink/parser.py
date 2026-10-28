"""Pure-Python phone state machine (no Home Assistant imports, easy to test)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

IDLE = "idle"
RINGING = "ringing"
DIALING = "dialing"
TALKING = "talking"
ON_HOLD = "on_hold"

FORWARD_TYPES = ("always", "busy", "no_answer")

PERSISTED_KEYS = (
    "incoming_total",
    "outgoing_total",
    "answered_total",
    "missed_total",
    "last_incoming_number",
    "last_incoming_name",
    "last_outgoing_number",
    "last_missed_number",
    "last_call_direction",
    "last_call_number",
    "last_call_duration",
    "last_call_time",
    "total_talk_seconds",
    "registration",
    "dnd",
    "forward_always",
    "forward_busy",
    "forward_no_answer",
    "mac",
    "ip",
    "model",
    "firmware",
    "active_user",
    "active_host",
    "last_boot",
    "last_ip_change",
)


def _clean(value: Any) -> str | None:
    """Return a stripped string, or None if empty or an unreplaced $variable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.startswith("$"):
        return None
    return text


class PhoneState:
    """Tracks everything we can infer from Action URL events."""

    def __init__(self) -> None:
        self.call_state = IDLE
        self.hook_off = False
        self.muted = False
        self.on_hold = False
        self.dnd = False
        self.forward_always = False
        self.forward_busy = False
        self.forward_no_answer = False
        self.registration: str | None = None
        self.direction: str | None = None
        self.remote_number: str | None = None
        self.remote_name: str | None = None
        self.local_number: str | None = None
        self.call_id: str | None = None
        self.call_started: datetime | None = None
        self.call_ring_started: datetime | None = None

        self.mac: str | None = None
        self.ip: str | None = None
        self.model: str | None = None
        self.firmware: str | None = None
        self.active_user: str | None = None
        self.active_host: str | None = None

        self.last_event: str | None = None
        self.last_event_time: datetime | None = None
        self.last_boot: datetime | None = None
        self.last_ip_change: datetime | None = None
        self.last_incoming_number: str | None = None
        self.last_incoming_name: str | None = None
        self.last_outgoing_number: str | None = None
        self.last_missed_number: str | None = None
        self.last_call_direction: str | None = None
        self.last_call_number: str | None = None
        self.last_call_duration: int | None = None
        self.last_call_time: datetime | None = None
        self.total_talk_seconds = 0

        self.incoming_total = 0
        self.outgoing_total = 0
        self.answered_total = 0
        self.missed_total = 0
        self.counter_day = None
        self.incoming_today = 0
        self.outgoing_today = 0
        self.missed_today = 0
        self.talk_seconds_today = 0

        self._established = False
        self._missed_counted = False
        self._missed_at: datetime | None = None

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in PERSISTED_KEYS:
            value = getattr(self, key)
            out[key] = value.isoformat() if isinstance(value, datetime) else value
        return out

    def load(self, data: dict[str, Any]) -> None:
        for key in PERSISTED_KEYS:
            if key not in data or data[key] is None:
                continue
            current = getattr(self, key)
            value = data[key]
            if key in ("last_boot", "last_ip_change", "last_call_time"):
                try:
                    value = datetime.fromisoformat(value)
                except (TypeError, ValueError):
                    continue
            elif isinstance(current, bool):
                value = bool(value)
            setattr(self, key, value)

    # -- helpers -----------------------------------------------------------
    def _roll_day(self, now: datetime) -> None:
        if self.counter_day != now.date():
            self.counter_day = now.date()
            self.incoming_today = self.outgoing_today = self.missed_today = 0
            self.talk_seconds_today = 0

    def _idle(self) -> None:
        self.call_state = IDLE
        self.on_hold = False
        self.direction = None
        self.remote_number = self.remote_name = None
        self.call_id = None
        self.call_started = self.call_ring_started = None
        self._established = False
        self._missed_counted = False

    def _count_missed(self, number: str | None, now: datetime) -> None:
        if self._missed_counted or (
            self._missed_at and (now - self._missed_at).total_seconds() < 10
        ):
            return
        self._missed_counted = True
        self._missed_at = now
        self.missed_total += 1
        self.missed_today += 1
        self.last_missed_number = number or self.last_missed_number

    def _finish_call(self, now: datetime) -> None:
        if self.direction is None and not self.remote_number:
            return
        duration = 0
        if self._established and self.call_started:
            duration = max(0, int((now - self.call_started).total_seconds()))
            self.total_talk_seconds += duration
            self.talk_seconds_today += duration
        elif self.direction == "incoming" and self.call_state == RINGING:
            self._count_missed(self.remote_number, now)
        self.last_call_direction = self.direction
        self.last_call_number = self.remote_number
        self.last_call_duration = duration
        self.last_call_time = now

    # -- event handling ----------------------------------------------------
    def apply(self, params: dict[str, Any], now: datetime) -> None:
        """Apply one Action URL event."""
        event = (_clean(params.get("event")) or "").lower()
        if not event:
            return
        self._roll_day(now)

        for attr in ("mac", "ip", "model", "firmware", "active_user", "active_host"):
            value = _clean(params.get(attr))
            if value:
                setattr(self, attr, value)

        remote = _clean(params.get("remote"))
        display_remote = _clean(params.get("display_remote"))
        local = _clean(params.get("local"))
        call_id = _clean(params.get("call_id"))
        if local:
            self.local_number = local

        self.last_event = event
        self.last_event_time = now

        if event == "setup_completed":
            self.last_boot = now
            self._idle()
            self.hook_off = False
        elif event == "registered":
            self.registration = "registered"
        elif event == "unregistered":
            self.registration = "unregistered"
        elif event == "register_failed":
            self.registration = "failed"
        elif event in ("off_hook", "headset", "handfree"):
            self.hook_off = True
        elif event == "on_hook":
            self.hook_off = False
            if self.call_state != IDLE:
                self._finish_call(now)
                self._idle()
        elif event == "incoming_call":
            self._idle()
            self.call_state = RINGING
            self.direction = "incoming"
            self.remote_number = remote
            self.remote_name = display_remote
            self.call_id = call_id
            self.call_ring_started = now
            self.incoming_total += 1
            self.incoming_today += 1
            self.last_incoming_number = remote or self.last_incoming_number
            self.last_incoming_name = display_remote or self.last_incoming_name
        elif event == "outgoing_call":
            self._idle()
            self.hook_off = True
            self.call_state = DIALING
            self.direction = "outgoing"
            self.remote_number = remote
            self.remote_name = display_remote
            self.call_id = call_id
            self.outgoing_total += 1
            self.outgoing_today += 1
            self.last_outgoing_number = remote or self.last_outgoing_number
        elif event == "call_established":
            self.call_state = TALKING
            self.hook_off = True
            self._established = True
            self.call_started = now
            self.answered_total += 1
            if remote:
                self.remote_number = remote
            if display_remote:
                self.remote_name = display_remote
            if self.direction is None:
                self.direction = "incoming"
        elif event in ("call_terminated", "rejected_incoming_call"):
            if event == "rejected_incoming_call":
                self._missed_counted = True
            self._finish_call(now)
            self._idle()
        elif event == "missed_call":
            self._count_missed(remote or self.remote_number, now)
            if self.call_state == RINGING:
                self.last_call_direction = "incoming"
                self.last_call_number = remote or self.remote_number
                self.last_call_duration = 0
                self.last_call_time = now
                self._idle()
        elif event in ("hold", "held"):
            self.on_hold = True
            if self.call_state == TALKING:
                self.call_state = ON_HOLD
        elif event in ("unhold", "unheld"):
            self.on_hold = False
            if self.call_state == ON_HOLD:
                self.call_state = TALKING
        elif event == "mute":
            self.muted = True
        elif event == "unmute":
            self.muted = False
        elif event in ("open_dnd", "close_dnd"):
            self.dnd = event == "open_dnd"
        elif event == "ip_change":
            self.last_ip_change = now
        elif "forward" in event and event.startswith(("open_", "close_")):
            enabled = event.startswith("open_")
            for ftype in FORWARD_TYPES:
                if ftype in event:
                    setattr(self, f"forward_{ftype}", enabled)
