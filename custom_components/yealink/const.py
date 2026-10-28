"""Constants for the Yealink IP Phone integration."""

from __future__ import annotations

DOMAIN = "yealink"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_WEBHOOK_ID = "webhook_id"
CONF_POLL_STATUS = "poll_status"

DEFAULT_NAME = "Yealink SIP-T31W"
DEFAULT_USERNAME = "admin"
POLL_INTERVAL_SECONDS = 60

STORAGE_VERSION = 1

# Events the phone can push through "Action URL" (Features > Action URL).
# key = phone parameter suffix (action_url.<key>), value = event name sent to HA.
ACTION_URL_EVENTS: tuple[str, ...] = (
    "setup_completed",
    "registered",
    "unregistered",
    "register_failed",
    "off_hook",
    "on_hook",
    "incoming_call",
    "outgoing_call",
    "call_established",
    "call_terminated",
    "missed_call",
    "rejected_incoming_call",
    "hold",
    "unhold",
    "held",
    "unheld",
    "mute",
    "unmute",
    "open_dnd",
    "close_dnd",
    "open_always_forward",
    "close_always_forward",
    "open_busy_forward",
    "close_busy_forward",
    "open_no_answer_forward",
    "close_no_answer_forward",
    "transfer_call",
    "blind_transfer",
    "attended_transfer",
    "transfer_finished",
    "transfer_failed",
    "forward_incoming_call",
    "answer_new_incoming_call",
    "ip_change",
    "headset",
    "handfree",
    "message_waiting",
    "autop_finish",
)

# Variables substituted by the phone in the Action URL.
ACTION_URL_VARIABLES: dict[str, str] = {
    "mac": "$mac",
    "ip": "$ip",
    "model": "$model",
    "firmware": "$firmware",
    "active_user": "$active_user",
    "active_host": "$active_host",
    "local": "$local",
    "remote": "$remote",
    "display_local": "$display_local",
    "display_remote": "$display_remote",
    "call_id": "$call_id",
}

# Action URI keys usable through /servlet?key=<KEY>.
ACTION_URI_KEYS: dict[str, str] = {
    "answer": "ENTER",
    "hangup": "CANCEL",
    "speaker": "SPEAKER",
    "headset": "HEADSET",
    "mute": "MUTE",
    "hold": "F_HOLD",
    "transfer": "F_TRANSFER",
    "conference": "F_CONFERENCE",
    "volume_up": "VOLUME_UP",
    "volume_down": "VOLUME_DOWN",
    "redial": "RD",
    "dnd_on": "DNDOn",
    "dnd_off": "DNDOff",
    "reboot": "Reboot",
}
