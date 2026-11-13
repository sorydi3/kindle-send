"""plugin/Service.qml end to end, under Qt's `qml` runtime with a fake
Quickshell.Io (tests/qmlfake/FakeIo): no command really runs, FakeWorld answers
for kindle-send and omarchy-notification-send and logs every call.

Skipped without /usr/lib/qt6/bin/qml. The decisions themselves are tested in
the pure JS tests; this checks the Service wires them up as spec §7, §10, §11 say.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FAKE = Path(__file__).resolve().parent / "qmlfake"
QML = shutil.which("qml6") or shutil.which("qml", path="/usr/lib/qt6/bin")

pytestmark = pytest.mark.skipif(QML is None, reason="Qt's qml runtime is not installed")

SCENARIO = """
import QtQuick
import FakeIo
import "plugin" as P

Item {
  P.Service { id: s }
  property int quiet: 0
  // Done once nothing is going on for a few polls in a row.
  Timer {
    interval: 50; repeat: true; running: true
    onTriggered: {
      const idle = !s.busy && s.held.length === 0 && s.pending.length === 0 && s.notifyQueue.length === 0
      quiet = idle ? quiet + 1 : 0
      if (quiet >= 4) Qt.quit()
    }
  }
  Timer { interval: 20000; running: true; onTriggered: { console.warn("EVENT {\\"kind\\":\\"timeout\\"}"); Qt.quit() } }
  Timer { interval: PLUG_AT; running: PLUG_AT > 0; onTriggered: FakeWorld.kindle = true }
  Component.onCompleted: {
    BODY
  }
}
"""


def run_service(tmp_path, body, plug_at=0):
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    for js in (ROOT / "plugin").glob("*.js"):
        shutil.copy(js, plugin)
    # Swap the real Quickshell imports for the fake, so nothing can really run.
    service = (ROOT / "plugin" / "Service.qml").read_text()
    service = service.replace("import Quickshell.Io\n", "import FakeIo\n").replace("import Quickshell\n", "")
    (plugin / "Service.qml").write_text(service)
    scenario = tmp_path / "scenario.qml"
    scenario.write_text(SCENARIO.replace("BODY", body).replace("PLUG_AT", str(plug_at)))
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_FORCE_STDERR_LOGGING": "1"}
    out = subprocess.run([QML, "-I", str(FAKE), str(scenario)], capture_output=True, text=True,
                         env=env, timeout=60)
    events = [json.loads(line.split("EVENT ", 1)[1]) for line in out.stderr.splitlines() if "EVENT " in line]
    assert events, out.stderr
    assert {"kind": "timeout"} not in [{"kind": e["kind"]} for e in events], events
    return events


def runs(events):
    return [e["cmd"] for e in events if e["kind"] == "run" and e["cmd"] != "kindle"]


def notices(events, id_):
    return [(e["urgency"], e["headline"]) for e in events if e["kind"] == "notify" and e["id"] == id_]


def first(events, pred):
    return next(i for i, e in enumerate(events) if pred(e))


CAPPED = "{ canSendIn: 1, sentLastHour: 20, maxEmailsPerHour: 20 }"
FREE = "{ canSendIn: 0, sentLastHour: 1, maxEmailsPerHour: 20 }"
GAP = "{ canSendIn: 1, sentLastHour: 1, maxEmailsPerHour: 20 }"


def book(name, route):
    return f'{{ path: "/b/{name}", name: "{name}", route: "{route}" }}'


def test_held_emails_dont_keep_the_kindle_mounted_or_block_later_sends(tmp_path):
    events = run_service(tmp_path, f"""
        FakeWorld.limits = [{CAPPED}, {CAPPED}, {FREE}]
        s.enqueue([{book("A.pdf", "usb")}, {book("B.epub", "email")}, {book("C.epub", "email")}])
        s.enqueue([{book("D.pdf", "usb")}])
    """)

    order = runs(events)
    # A copies and the Kindle is ejected at once; D (a later Send) goes before the held emails.
    assert order.index("send --route usb /b/A.pdf") < order.index("eject")
    assert order.index("send --route usb /b/D.pdf") < order.index("send --route email /b/B.epub")
    assert order.index("send --route email /b/B.epub") < order.index("send --route email /b/C.epub")
    # The first Send's notification ends in the USB part's summary.
    assert notices(events, 100)[-1] == ("normal", "A.pdf")
    # The hold notice is its own critical notification, then the emails' summary.
    hold_id = next(e["id"] for e in events if e["kind"] == "notify" and e["headline"].startswith("Holding"))
    assert hold_id != 100
    assert notices(events, hold_id)[0] == ("critical", "Holding 2 Books to stay under Amazon's limit.")
    assert all(u == "critical" for u, h in notices(events, hold_id)[:-1])
    assert notices(events, hold_id)[-1] == ("normal", "Sent 2 Books")


def test_the_hold_notice_counts_down_as_held_emails_go(tmp_path):
    events = run_service(tmp_path, f"""
        FakeWorld.limits = [{CAPPED}, {CAPPED}, {FREE}, {CAPPED}, {FREE}]
        s.enqueue([{book("B.epub", "email")}, {book("C.epub", "email")}])
    """)

    headlines = [h for u, h in notices(events, 100)]
    assert "Holding 2 Books to stay under Amazon's limit." in headlines
    assert headlines.index("Holding 1 Book to stay under Amazon's limit.") \
        > headlines.index("Holding 2 Books to stay under Amazon's limit.")
    assert headlines[-1] == "Sent 2 Books"


def test_a_gap_wait_stays_in_its_send_with_no_notice(tmp_path):
    events = run_service(tmp_path, f"""
        FakeWorld.limits = [{FREE}, {GAP}, {FREE}]
        s.enqueue([{book("B.epub", "email")}, {book("C.epub", "email")}])
    """)

    assert {e["id"] for e in events if e["kind"] == "notify"} == {100}
    assert not any(h.startswith("Holding") for u, h in notices(events, 100))
    assert notices(events, 100)[-1] == ("normal", "Sent 2 Books")


def test_books_released_by_a_pending_send_go_while_emails_are_held(tmp_path):
    events = run_service(tmp_path, f"""
        FakeWorld.kindle = false
        FakeWorld.limits = [{CAPPED}]
        s.enqueue([{book("D.pdf", "usb")}, {book("E.epub", "email")}])
        // Lift the cap only after the Kindle has been plugged in and D has gone.
        FakeWorld.later(function() {{ FakeWorld.limits = [{FREE}] }}, 4500)
    """, plug_at=1000)

    order = runs(events)
    copied = [i for i, c in enumerate(order) if c == "send --route usb /b/D.pdf"]
    assert len(copied) == 2  # once without a Kindle, once after the plug-in
    assert copied[1] < order.index("eject") < order.index("send --route email /b/E.epub")


# --- Failure clicks (spec §10, §13) -------------------------------------------

SUMMON = ["omarchy-shell", "shell", "summon", "sorydi3.kindle-send"]


def summary_click(events):
    """The --exec argv of the Send's last notification (its summary)."""
    return [e for e in events if e["kind"] == "notify" and e["id"] == 100][-1]["exec"]


@pytest.mark.parametrize("reason, field", [
    ("Not set up: kindleAddress missing.", "kindleAddress"),
    ("Not set up: senderAddress missing.", "senderAddress"),
    ("No app password stored.", "appPassword"),
    ("Gmail rejected the app password.", "appPassword"),
])
def test_a_failure_a_setting_fixes_opens_settings_on_that_field_when_clicked(tmp_path, reason, field):
    failed = {"result": "failed", "reason": reason, "fixBySetup": True, "field": field}
    events = run_service(tmp_path, f"""
        FakeWorld.limits = [{FREE}]
        FakeWorld.sendResults = {{ "/b/B.epub": {json.dumps(failed)} }}
        s.enqueue([{book("B.epub", "email")}])
    """)

    click = summary_click(events)
    assert click[:4] == SUMMON
    assert json.loads(click[4]) == {"settings": field, "problem": reason}
    assert len(click) == 5


def test_a_failure_no_setting_fixes_has_no_click(tmp_path):
    failed = {"result": "failed", "reason": "Too big for email (60 MB). Switch it to USB."}
    events = run_service(tmp_path, f"""
        FakeWorld.limits = [{FREE}]
        FakeWorld.sendResults = {{ "/b/B.epub": {json.dumps(failed)} }}
        s.enqueue([{book("B.epub", "email")}])
    """)

    assert summary_click(events) == []


def test_a_held_email_failing_on_a_setting_opens_settings_on_that_field(tmp_path):
    failed = {"result": "failed", "reason": "Gmail rejected the app password.", "fixBySetup": True,
              "field": "appPassword"}
    events = run_service(tmp_path, f"""
        FakeWorld.limits = [{CAPPED}, {CAPPED}, {FREE}]
        FakeWorld.sendResults = {{ "/b/B.epub": {json.dumps(failed)} }}
        s.enqueue([{book("B.epub", "email")}])
    """)

    last = [e for e in events if e["kind"] == "notify"][-1]
    assert last["headline"] == "Couldn't send B.epub"
    assert last["exec"][:4] == SUMMON
    assert json.loads(last["exec"][4])["settings"] == "appPassword"


def test_no_notification_click_runs_the_terminal_wizard(tmp_path):
    failed = {"result": "failed", "reason": "No app password stored.", "fixBySetup": True, "field": "appPassword"}
    events = run_service(tmp_path, f"""
        FakeWorld.kindle = false
        FakeWorld.limits = [{CAPPED}, {FREE}]
        FakeWorld.sendResults = {{ "/b/B.epub": {json.dumps(failed)} }}
        s.enqueue([{book("B.epub", "email")}, {book("D.pdf", "usb")}])
    """, plug_at=1000)

    clicks = [e["exec"] for e in events if e["kind"] == "notify" and e["exec"]]
    assert clicks
    assert not any("setup" in c or "omarchy-launch-floating-terminal-with-presentation" in c for c in clicks)
