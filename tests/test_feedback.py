"""plugin/Feedback.js: what the Send notification says (spec §10). Run with node."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

FEEDBACK = Path(__file__).resolve().parent.parent / "plugin" / "Feedback.js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

# Loads the QML JS library (minus `.pragma library`) and calls one function with JSON args.
RUNNER = r"""
const fs = require("fs"), vm = require("vm")
const src = fs.readFileSync(process.argv[1], "utf8").replace(/^\.pragma library.*$/m, "")
const ctx = {}
vm.createContext(ctx)
vm.runInContext(src + "\nthis.__lib = { summary, progressAt, stageAt, resultFor, needsEject, notifyArgv }", ctx)
const [name, args] = JSON.parse(process.argv[2])
process.stdout.write(JSON.stringify(ctx.__lib[name](...args)))
"""


def call(name, *args):
    out = subprocess.run([NODE, "-e", RUNNER, str(FEEDBACK), json.dumps([name, list(args)])],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


EJECTED = {"ejected": True}
NOT_EJECTED = {"ejected": False, "reason": "target is busy"}


def test_one_book_copied_and_ejected_says_safe_to_unplug():
    s = call("summary", [{"name": "Atlas.pdf", "result": "copied"}], EJECTED)

    assert s == {"headline": "Atlas.pdf", "body": "Copied to Kindle. Kindle ejected, safe to unplug.",
                 "urgency": "normal", "setup": False, "timeout": 5000}


def test_eject_failure_asks_the_user_to_eject_and_stays_on_screen():
    s = call("summary", [{"name": "Atlas.pdf", "result": "copied"}], NOT_EJECTED)

    assert s["body"] == "Copied to Kindle. Please eject the Kindle."
    assert s["urgency"] == "critical"


def test_mixed_send_lists_each_route_result():
    results = [{"name": "Dune.epub", "result": "sent"}, {"name": "Atlas.pdf", "result": "copied"}]

    s = call("summary", results, EJECTED)

    assert s["headline"] == "Sent 2 Books"
    assert s["body"] == ("Dune.epub: Sent to Amazon.\nAtlas.pdf: Copied to Kindle.\n"
                         "Should appear on your Kindle within a few minutes.\n"
                         "Kindle ejected, safe to unplug.")
    assert s["urgency"] == "normal"


def test_email_only_send_has_no_eject_line():
    s = call("summary", [{"name": "Dune.epub", "result": "sent"}], None)

    assert s["body"] == "Sent to Amazon. Should appear on your Kindle within a few minutes."


def test_failed_usb_book_without_eject_names_the_reason():
    s = call("summary", [{"name": "Atlas.pdf", "result": "failed",
                          "reason": "Kindle not plugged in. Plug it in and send again."}], None)

    assert s["headline"] == "Couldn't send Atlas.pdf"
    assert s["body"] == "Kindle not plugged in. Plug it in and send again."
    assert s["urgency"] == "critical"


def test_copying_stage_updates_the_notification():
    books = [{"name": "Dune.epub"}, {"name": "Atlas.pdf"}]

    assert call("stageAt", books, 1, "copying") == {"headline": "Copying to Kindle…",
                                                     "body": "2 of 2: Atlas.pdf"}
    assert call("stageAt", books[1:], 0, "copying") == {"headline": "Copying to Kindle…",
                                                         "body": "Atlas.pdf"}
    assert call("stageAt", books, 0, "sending") is None


@pytest.mark.parametrize("results, wanted", [
    ([{"result": "sent"}], False),
    ([{"result": "sent"}, {"result": "copied"}], True),
    ([{"result": "copied"}, {"result": "failed"}], True),
    ([{"result": "failed"}], False),
])
def test_eject_once_a_send_copied_anything(results, wanted):
    assert call("needsEject", results) is wanted


# --- Failures (spec §10, §13) ------------------------------------------------

PASSWORD = {"name": "Dune.epub", "result": "failed", "reason": "Gmail rejected the app password.",
            "fixBySetup": True}
TOO_BIG = {"name": "Atlas.pdf", "result": "failed", "reason": "Too big for email (60 MB). Switch it to USB."}


def test_every_failed_book_is_listed_with_its_reason_and_stays_on_screen():
    results = [PASSWORD, {"name": "Emma.epub", "result": "sent"}, TOO_BIG]

    s = call("summary", results, None)

    assert s["headline"] == "2 Books of 3 failed"
    assert s["body"].splitlines()[:3] == [
        "Dune.epub: Gmail rejected the app password.",
        "Emma.epub: Sent to Amazon.",
        "Atlas.pdf: Too big for email (60 MB). Switch it to USB.",
    ]
    assert s["urgency"] == "critical"


def test_a_failure_setup_fixes_makes_a_click_open_setup():
    assert call("summary", [PASSWORD], None)["setup"] is True
    assert call("summary", [TOO_BIG, PASSWORD], None)["setup"] is True


def test_a_failure_setup_cannot_fix_does_not_open_setup():
    s = call("summary", [TOO_BIG], None)

    assert s["headline"] == "Couldn't send Atlas.pdf"
    assert s["body"] == "Too big for email (60 MB). Switch it to USB."
    assert s["setup"] is False


def test_a_successful_send_times_out_after_a_few_seconds():
    s = call("summary", [{"name": "Dune.epub", "result": "sent"}], None)

    assert s["urgency"] == "normal"
    assert s["timeout"] == 5000


def test_a_failed_send_has_no_timeout():
    assert "timeout" not in call("summary", [TOO_BIG], None)


SETUP = ["omarchy-launch-floating-terminal-with-presentation", "kindle-send", "setup"]
POST = ["omarchy-notification-send", "--app-name", "Send to Kindle", "-g", "\uF02D"]


def test_first_post_asks_for_the_id_and_a_done_summary_times_out():
    item = {"headline": "Dune.epub", "body": "Sent to Amazon.", "urgency": "normal", "timeout": 5000}

    assert call("notifyArgv", item, 0) == POST + ["-u", "normal", "-t", "5000", "-p",
                                                  "Dune.epub", "Sent to Amazon."]


def test_a_failure_that_setup_fixes_replaces_in_place_and_opens_setup_on_click():
    item = {"headline": "Couldn't send Dune.epub", "body": "No app password stored.",
            "urgency": "critical", "exec": SETUP}

    assert call("notifyArgv", item, 7) == POST + ["-u", "critical", "-r", "7",
                                                  "Couldn't send Dune.epub", "No app password stored.",
                                                  "--exec"] + SETUP
