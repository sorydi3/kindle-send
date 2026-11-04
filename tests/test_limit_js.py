"""plugin/Limit.js, run under node (skipped without node): how the Service keeps to the Send limit."""
import json
import subprocess
from pathlib import Path

import pytest

from test_rows_js import HARNESS, NODE

LIMIT_JS = Path(__file__).resolve().parent.parent / "plugin" / "Limit.js"

pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")


def js(expr):
    out = subprocess.run([NODE, "-e", HARNESS, str(LIMIT_JS), expr],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def books(*routes):
    return json.dumps([{"path": f"/b/{i}", "name": f"Book{i}.epub", "route": r}
                       for i, r in enumerate(routes)])


def state(can_send_in, sent_last_hour=1, per_hour=20):
    return json.dumps({"canSendIn": can_send_in, "sentLastHour": sent_last_hour,
                       "maxEmailsPerHour": per_hour})


def test_a_usb_book_is_never_limited():
    assert js(f"decide({books('usb')}, 0, {state(600, 20)})") == {"action": "send"}


def test_an_email_goes_when_the_limit_allows():
    assert js(f"decide({books('email')}, 0, {state(0)})") == {"action": "send"}


def test_an_email_inside_the_gap_waits_without_being_held():
    assert js(f"decide({books('email')}, 0, {state(6)})") == {"action": "wait", "ms": 6000, "held": False}


def test_an_email_over_the_hourly_cap_is_held():
    assert js(f"decide({books('email', 'email')}, 1, {state(600, 20)})") \
        == {"action": "wait", "ms": 600000, "held": True}


def test_a_usb_book_further_on_goes_ahead_of_a_waiting_email():
    decision = js(f"decide({books('usb', 'email', 'email', 'usb', 'email')}, 1, {state(600, 20)})")

    assert decision["action"] == "send"
    assert [b["name"] for b in decision["books"]] == \
        ["Book0.epub", "Book3.epub", "Book1.epub", "Book2.epub", "Book4.epub"]


def test_holding_counts_the_emails_left_in_this_send_and_the_queued_ones():
    queue = json.dumps([{"id": 2, "books": json.loads(books("email", "usb"))}])

    text = js(f"holding({books('email', 'email', 'email')}, 1, {queue}, 600)")

    assert text == {"headline": "Holding 3 Books to stay under Amazon's limit.", "body": "Next in 10 min."}


def test_holding_one_book_rounds_the_minutes_up():
    assert js(f"holding({books('email')}, 0, [], 61)") \
        == {"headline": "Holding 1 Book to stay under Amazon's limit.", "body": "Next in 2 min."}


def test_holding_says_at_least_one_minute():
    assert js(f"holding({books('email')}, 0, [], 5)")["body"] == "Next in 1 min."


def test_parse_reads_the_limit_line():
    assert js('parse([{"stage": "x"}, {"canSendIn": 6, "sentLastHour": 2, "maxEmailsPerHour": 20}])') \
        == {"canSendIn": 6, "sentLastHour": 2, "maxEmailsPerHour": 20}


def test_parse_without_a_limit_line_gives_null():
    assert js("parse([])") is None


def test_without_a_limit_answer_the_email_goes_anyway():
    """If `kindle-send limit` gave nothing usable, sending beats stalling forever."""
    assert js(f"decide({books('email')}, 0, null)") == {"action": "send"}
