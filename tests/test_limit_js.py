"""Limit.js, run under node (skipped without node): how the Service keeps to the Send limit.

Emails the hourly cap holds back leave their Send and wait in the Service's
held-email line, so USB Books and later Sends don't wait for them (spec §7, §11).
"""
import json

from qmljs import evaluate, needs_node

pytestmark = needs_node


def js(expr):
    return evaluate("Limit.js", expr)


def books(*routes):
    return json.dumps([{"path": f"/b/{i}", "name": f"Book{i}.epub", "route": r}
                       for i, r in enumerate(routes)])


def names(list_):
    return [b["name"] for b in list_]


def state(can_send_in, sent_last_hour=1, per_hour=20):
    return json.dumps({"canSendIn": can_send_in, "sentLastHour": sent_last_hour,
                       "maxEmailsPerHour": per_hour})


CAPPED = state(600, 20)


def test_a_usb_book_is_never_limited():
    assert js(f"decide({books('usb')}, 0, {CAPPED}, true)") == {"action": "send"}


def test_an_email_goes_when_the_limit_allows():
    assert js(f"decide({books('email')}, 0, {state(0)}, false)") == {"action": "send"}


def test_without_a_limit_answer_the_email_goes_anyway():
    """If `kindle-send limit` gave nothing usable, sending beats stalling forever."""
    assert js(f"decide({books('email')}, 0, null, false)") == {"action": "send"}


def test_an_email_inside_the_gap_waits_in_its_send():
    """A gap wait is seconds: the Send waits it out, with no notice."""
    assert js(f"decide({books('email')}, 0, {state(6)}, false)") == {"action": "wait", "ms": 6000}


def test_a_usb_book_further_on_goes_ahead_of_an_email_inside_the_gap():
    decision = js(f"decide({books('usb', 'email', 'email', 'usb', 'email')}, 1, {state(6)}, false)")

    assert decision["action"] == "send"
    assert names(decision["books"]) == ["Book0.epub", "Book3.epub", "Book1.epub", "Book2.epub", "Book4.epub"]


def test_over_the_hourly_cap_the_rest_of_the_sends_emails_are_held_and_its_usb_books_stay():
    decision = js(f"decide({books('usb', 'email', 'email', 'usb', 'email')}, 1, {CAPPED}, false)")

    assert decision["action"] == "hold"
    assert names(decision["books"]) == ["Book0.epub", "Book3.epub"]
    assert names(decision["held"]) == ["Book1.epub", "Book2.epub", "Book4.epub"]
    assert decision["notice"] is True


def test_while_emails_are_held_a_new_email_joins_them_without_asking_the_limit():
    """One email at a time, in order: the held line goes first."""
    decision = js(f"decide({books('email', 'usb')}, 0, null, true)")

    assert decision["action"] == "hold"
    assert names(decision["books"]) == ["Book1.epub"]
    assert names(decision["held"]) == ["Book0.epub"]
    assert decision["notice"] is False


def test_the_held_line_sends_when_the_limit_allows():
    assert js(f"heldStep({state(0)}, false)") == {"action": "send"}
    assert js("heldStep(null, true)") == {"action": "send"}


def test_the_held_line_waits_out_a_gap_without_a_notice():
    assert js(f"heldStep({state(8)}, false)") == {"action": "wait", "ms": 8000, "notice": False}


def test_the_held_line_keeps_its_notice_up_through_a_gap():
    assert js(f"heldStep({state(8)}, true)") == {"action": "wait", "ms": 8000, "notice": True}


def test_the_held_line_over_the_cap_shows_the_notice():
    assert js(f"heldStep({CAPPED}, false)") == {"action": "wait", "ms": 600000, "notice": True}


def test_the_hold_notice_stays_on_screen():
    assert js("holding(3, 600)") == {"headline": "Holding 3 Books to stay under Amazon's limit.",
                                     "body": "Next in 10 min.", "urgency": "critical"}


def test_holding_one_book_rounds_the_minutes_up():
    assert js("holding(1, 61)")["headline"] == "Holding 1 Book to stay under Amazon's limit."
    assert js("holding(1, 61)")["body"] == "Next in 2 min."


def test_holding_says_at_least_one_minute():
    assert js("holding(2, 5)")["body"] == "Next in 1 min."


def test_parse_reads_the_limit_line():
    assert js('parse([{"stage": "x"}, {"canSendIn": 6, "sentLastHour": 2, "maxEmailsPerHour": 20}])') \
        == {"canSendIn": 6, "sentLastHour": 2, "maxEmailsPerHour": 20}


def test_parse_without_a_limit_line_gives_null():
    assert js("parse([])") is None
