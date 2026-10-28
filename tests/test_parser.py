import importlib.util
import pathlib
from datetime import datetime, timedelta

spec = importlib.util.spec_from_file_location(
    "yealink_parser",
    pathlib.Path(__file__).parent.parent / "custom_components/yealink/parser.py",
)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

T0 = datetime(2026, 1, 1, 12, 0, 0)


def ev(state, name, at=0, **kw):
    state.apply({"event": name, **kw}, T0 + timedelta(seconds=at))


def test_incoming_answered():
    s = parser.PhoneState()
    ev(s, "incoming_call", remote="0612345678", display_remote="Bob", call_id="1")
    assert s.call_state == parser.RINGING and s.remote_name == "Bob"
    ev(s, "call_established", at=2)
    assert s.call_state == parser.TALKING
    ev(s, "call_terminated", at=62)
    assert s.call_state == parser.IDLE
    assert s.last_call_duration == 60 and s.answered_total == 1
    assert s.missed_total == 0 and s.incoming_today == 1


def test_missed_call_counted_once():
    s = parser.PhoneState()
    ev(s, "incoming_call", remote="100")
    ev(s, "call_terminated", at=5)
    ev(s, "missed_call", at=5, remote="100")
    assert s.missed_total == 1 and s.last_missed_number == "100"


def test_outgoing_hold_mute_dnd():
    s = parser.PhoneState()
    ev(s, "outgoing_call", remote="200")
    assert s.call_state == parser.DIALING and s.hook_off
    ev(s, "call_established", at=1)
    ev(s, "hold", at=2)
    assert s.call_state == parser.ON_HOLD
    ev(s, "unhold", at=3)
    ev(s, "mute", at=4)
    ev(s, "open_dnd")
    ev(s, "open_always_forward")
    assert s.muted and s.dnd and s.forward_always
    ev(s, "on_hook", at=10)
    assert s.call_state == parser.IDLE and s.last_call_number == "200"


def test_unreplaced_variables_ignored_and_persistence():
    s = parser.PhoneState()
    ev(s, "registered", mac="$mac", ip="192.168.1.5", model="SIP-T31W")
    assert s.mac is None and s.ip == "192.168.1.5" and s.registration == "registered"
    s2 = parser.PhoneState()
    s2.load(s.to_dict())
    assert s2.ip == "192.168.1.5" and s2.registration == "registered"
