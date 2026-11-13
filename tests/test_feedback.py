"""plugin/Feedback.js: what the Send notification says (spec §10). Run with node."""
import json

import pytest

from qmljs import evaluate, needs_node

pytestmark = needs_node


def call(name, *args):
    return evaluate("Feedback.js", f"{name}(...{json.dumps(list(args))})")


EJECTED = {"ejected": True}
NOT_EJECTED = {"ejected": False, "reason": "target is busy"}


def test_one_book_copied_and_ejected_says_safe_to_unplug():
    s = call("summary", [{"name": "Atlas.pdf", "result": "copied"}], EJECTED)

    assert s == {"headline": "Atlas.pdf", "body": "Copied to Kindle. Kindle ejected, safe to unplug.",
                 "urgency": "normal", "fix": None, "timeout": 5000}


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


def test_converting_stage_names_the_book():
    books = [{"name": "Dune.epub"}, {"name": "Atlas.pdf"}]

    assert call("stageAt", books, 0, "converting") == {"headline": "Converting Dune.epub…",
                                                       "body": "1 of 2"}
    assert call("stageAt", books[:1], 0, "converting") == {"headline": "Converting Dune.epub…",
                                                           "body": ""}


@pytest.mark.parametrize("results, wanted", [
    ([{"result": "sent"}], False),
    ([{"result": "sent"}, {"result": "copied"}], True),
    ([{"result": "copied"}, {"result": "failed"}], True),
    ([{"result": "failed"}], False),
])
def test_eject_once_a_send_copied_anything(results, wanted):
    assert call("needsEject", results) is wanted


def send_of(*routes):
    return [{"path": f"/b/{i}", "name": f"Book{i}", "route": r} for i, r in enumerate(routes)]


COPIED = [{"name": "Book0", "result": "copied"}]


@pytest.mark.parametrize("books, index, results, ejected, step", [
    (send_of("usb", "usb"), 1, COPIED, False, "book"),
    # Eject as soon as no USB Book is left, before the Send's remaining emails.
    (send_of("usb", "email"), 1, COPIED, False, "eject"),
    (send_of("usb", "email"), 1, COPIED, True, "book"),
    (send_of("usb"), 1, COPIED, False, "eject"),
    (send_of("usb"), 1, COPIED, True, "finish"),
    (send_of("email"), 1, [{"name": "Book0", "result": "sent"}], False, "finish"),
    # Nothing copied (no Kindle, a failure): nothing to eject.
    (send_of("usb"), 1, [], False, "finish"),
])
def test_after_a_book_the_send_goes_on_ejects_or_finishes(books, index, results, ejected, step):
    assert call("nextStep", books, index, results, ejected) == step


# --- Failures (spec §10, §13) ------------------------------------------------

PASSWORD = {"name": "Dune.epub", "result": "failed", "reason": "Gmail rejected the app password.",
            "fixBySetup": True, "field": "appPassword"}
MISSING = {"name": "Emma.epub", "result": "failed", "reason": "Not set up: kindleAddress missing.",
           "fixBySetup": True, "field": "kindleAddress"}
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


def test_a_failure_a_setting_fixes_names_that_field_and_its_reason():
    assert call("summary", [PASSWORD], None)["fix"] == {
        "field": "appPassword", "reason": "Gmail rejected the app password."}
    assert call("summary", [TOO_BIG, PASSWORD], None)["fix"]["field"] == "appPassword"


def test_with_several_fixable_failures_the_first_one_is_the_fix():
    assert call("summary", [MISSING, PASSWORD], None)["fix"]["field"] == "kindleAddress"


def test_a_click_on_a_fixable_failure_summons_the_picker_into_settings_on_the_field():
    fix = {"field": "appPassword", "reason": "Gmail rejected the app password."}

    argv = call("settingsArgv", "sorydi3.kindle-send", fix)

    assert argv[:4] == ["omarchy-shell", "shell", "summon", "sorydi3.kindle-send"]
    assert json.loads(argv[4]) == {"settings": "appPassword", "problem": "Gmail rejected the app password."}
    assert len(argv) == 5


def test_no_fix_means_no_click():
    assert call("settingsArgv", "sorydi3.kindle-send", None) == []


def test_a_failure_setup_cannot_fix_does_not_open_setup():
    s = call("summary", [TOO_BIG], None)

    assert s["headline"] == "Couldn't send Atlas.pdf"
    assert s["body"] == "Too big for email (60 MB). Switch it to USB."
    assert s["fix"] is None


def test_a_successful_send_times_out_after_a_few_seconds():
    s = call("summary", [{"name": "Dune.epub", "result": "sent"}], None)

    assert s["urgency"] == "normal"
    assert s["timeout"] == 5000


def test_a_failed_send_has_no_timeout():
    assert "timeout" not in call("summary", [TOO_BIG], None)


SETUP = ["omarchy-shell", "shell", "summon", "sorydi3.kindle-send", '{"settings":"appPassword"}']
POST = ["omarchy-notification-send", "--app-name", "Send to Kindle", "-g", "\uF02D"]


def test_first_post_asks_for_the_id_and_a_done_summary_times_out():
    item = {"headline": "Dune.epub", "body": "Sent to Amazon.", "urgency": "normal", "timeout": 5000}

    assert call("notifyArgv", item, 0) == POST + ["-u", "normal", "-t", "5000", "-p",
                                                  "Dune.epub", "Sent to Amazon."]


def test_a_failure_a_setting_fixes_replaces_in_place_and_opens_settings_on_click():
    item = {"headline": "Couldn't send Dune.epub", "body": "No app password stored.",
            "urgency": "critical", "exec": SETUP}

    assert call("notifyArgv", item, 7) == POST + ["-u", "critical", "-r", "7",
                                                  "Couldn't send Dune.epub", "No app password stored.",
                                                  "--exec"] + SETUP


def test_a_send_result_keeps_the_field_at_fault():
    line = {"result": "failed", "reason": "No app password stored.", "fixBySetup": True, "field": "appPassword"}

    r = call("resultFor", {"name": "Dune.epub"}, [{"stage": "sending"}, line], 0, True)

    assert r == {"name": "Dune.epub", "result": "failed", "reason": "No app password stored.",
                 "fixBySetup": True, "field": "appPassword"}


# --- The test send (spec §9, §10) ---------------------------------------------

TEST_SENT = ("Sent to Amazon. Not on your Kindle in a few minutes? Check that sender@gmail.com is on "
             "Amazon's approved list and the Kindle address is right.")
SUMMON_SETTINGS = ["omarchy-shell", "shell", "summon", "sorydi3.kindle-send", '{"settings":""}']


def test_the_test_book_runs_send_with_test_instead_of_a_file():
    book = call("testBook", "sender@gmail.com")

    assert book["name"] == "Kindle Send Test"
    assert book["route"] == "email"
    assert call("sendArgv", book) == ["kindle-send", "send", "--route", "email", "--test"]


def test_any_other_book_runs_send_with_its_path():
    book = {"path": "/b/Dune.epub", "name": "Dune.epub", "route": "email"}

    assert call("sendArgv", book) == ["kindle-send", "send", "--route", "email", "/b/Dune.epub"]


def test_a_sent_test_book_lists_the_usual_causes_instead_of_a_question():
    book = call("testBook", "sender@gmail.com")
    result = call("resultFor", book, [{"stage": "sending"}, {"result": "sent"}], 0, True)

    s = call("summary", [result], None)

    assert s["headline"] == "Kindle Send Test"
    assert s["body"] == TEST_SENT
    assert s["urgency"] == "normal"


def test_clicking_a_sent_test_book_opens_settings():
    book = call("testBook", "sender@gmail.com")
    result = call("resultFor", book, [{"result": "sent"}], 0, True)

    assert call("clickArgv", "sorydi3.kindle-send", call("summary", [result], None)) == SUMMON_SETTINGS


def test_clicking_a_failed_test_book_opens_settings_on_its_field_or_else_on_settings():
    book = call("testBook", "sender@gmail.com")
    rejected = call("resultFor", book, [{"result": "failed", "reason": "Gmail rejected the app password.",
                                         "fixBySetup": True, "field": "appPassword"}], 0, True)
    offline = call("resultFor", book, [{"result": "failed", "reason": "Couldn't reach Gmail."}], 0, True)

    on_field = call("clickArgv", "sorydi3.kindle-send", call("summary", [rejected], None))
    assert json.loads(on_field[4]) == {"settings": "appPassword", "problem": "Gmail rejected the app password."}
    assert call("clickArgv", "sorydi3.kindle-send", call("summary", [offline], None)) == SUMMON_SETTINGS


def test_clicking_an_ordinary_send_opens_settings_only_for_a_fix():
    sent = call("summary", [{"name": "Dune.epub", "result": "sent"}], None)
    rejected = call("summary", [{"name": "Dune.epub", "result": "failed", "reason": "No app password stored.",
                                 "fixBySetup": True, "field": "appPassword"}], None)

    assert call("clickArgv", "sorydi3.kindle-send", sent) == []
    assert json.loads(call("clickArgv", "sorydi3.kindle-send", rejected)[4])["settings"] == "appPassword"
