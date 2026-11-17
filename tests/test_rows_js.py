"""Rows.js, run under node (skipped without node): the Picker's row text."""
import json

import pytest

from qmljs import evaluate, needs_node

pytestmark = needs_node

NOW = "Date.parse('2026-11-05T12:00:00Z')"


def rows(expr):
    return evaluate("Rows.js", expr)


def book(**fields):
    base = {"name": "Dune.epub", "format": "epub", "size": 1_200_000, "route": "email",
            "routeReason": "", "emailOk": True, "usbOk": True, "lastSent": None}
    return json.dumps({**base, **fields})


def test_a_book_sent_three_days_ago_says_so():
    text = rows(f"details({book(lastSent='2026-11-02T11:00:00+00:00')}, 'email', {NOW}, EN)")

    assert text == "EPUB · 1.2 MB · sent 3 days ago"


def test_a_book_sent_yesterday():
    assert rows(f"details({book(lastSent='2026-11-04T09:00:00+00:00')}, 'email', {NOW}, EN)") \
        == "EPUB · 1.2 MB · sent yesterday"


def test_a_book_never_sent_has_no_mark():
    assert rows(f"details({book()}, 'email', {NOW}, EN)") == "EPUB · 1.2 MB"


def test_an_already_sent_book_is_sent_again_like_any_other():
    """Re-sending needs no confirmation: marking a sent Book sends it."""
    chosen = rows(f"toSend([{book(path='/b/Dune.epub', lastSent='2026-11-02T11:00:00+00:00')}],"
                  " {'/b/Dune.epub': true}, {}, 0)")

    assert chosen == [{"path": "/b/Dune.epub", "name": "Dune.epub", "route": "email"}]


def test_enter_on_the_waiting_line_sends_nothing():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"toSend([{book(path='/b/Dune.epub')}], {{}}, {{}}, {waiting})") == []


def test_a_plan_that_needs_setup_sends_the_picker_into_settings():
    """The Picker then opens straight into Settings, titled "Set up Books to Kindle" (spec §4, §9)."""
    parsed = rows("fromPlan([{setupNeeded: true, missing: ['appPassword']},"
                  f" {book(path='/b/Dune.epub')}])")

    assert parsed["setupNeeded"] is True
    assert parsed["missing"] == ["appPassword"]


def test_a_plan_without_setup_needed_lists_books():
    parsed = rows(f"fromPlan([{book(path='/b/Dune.epub')}])")

    assert parsed["setupNeeded"] is False
    assert [b["path"] for b in parsed["books"]] == ["/b/Dune.epub"]


PROGRAM = "/p/sorydi3.kindle-send/bin/kindle-send"


def test_plan_info_gives_the_book_folders():
    parsed = rows(f"fromPlan([{{bookFolders: ['~/Library']}}, {book(path='/b/Dune.epub')}])")

    assert parsed["bookFolders"] == ["~/Library"]
    assert [b["path"] for b in parsed["books"]] == ["/b/Dune.epub"]
    assert "routeLabels" not in parsed


def test_without_plan_info_the_empty_state_names_no_folders():
    assert rows("fromPlan([])")["bookFolders"] == []
    assert rows("emptyMessage([], EN)") == "No Books found in your Book folders"


def test_the_plugin_names_the_routes_itself():
    """plan sends Route ids only (spec §17, Translations)."""
    assert rows("[routeLabel('email', EN), routeLabel('usb', EN)]") == ["Email", "USB"]
    assert rows("[Routes.label('email', EN), Routes.label('usb', EN)]") == ["Email", "USB"]


def test_route_labels_come_from_the_catalog():
    assert rows("routeLabel('email', LANG({'route.email': 'Correo'}))") == "Correo"
    assert rows(f"details({book(usbOk=False)}, 'usb', {NOW}, LANG({{'route.usb': 'USB-Kabel'}}))") \
        == "EPUB · 1,2 MB · USB-Kabel can't take this Book"


def test_a_route_with_no_label_shows_its_id():
    assert rows("routeLabel('carrier-pigeon', EN)") == "carrier-pigeon"


def test_a_route_the_book_cant_take_is_named_in_details():
    text = rows(f"details({book(usbOk=False)}, 'usb', {NOW}, EN)")

    assert text == "EPUB · 1.2 MB · USB can't take this Book"


def test_tab_switches_between_the_two_routes():
    assert rows("[switchRoute('email'), switchRoute('usb')]") == ["usb", "email"]


# --- What Enter will send, said in the footer -----------------------------

def footer(books, marked="{}", overrides="{}", highlighted="null"):
    return rows(f"footer([{', '.join(books)}], {marked}, {overrides}, {highlighted}, EN)")


def test_with_nothing_marked_enter_sends_the_highlighted_book():
    dune = book(path="/b/Dune.epub")

    assert footer([dune], highlighted=dune) == {"status": "", "enter": "Send this Book"}


def test_with_books_marked_enter_says_how_many_go():
    dune, atlas = book(path="/b/Dune.epub"), book(path="/b/Atlas.pdf", name="Atlas.pdf")

    assert footer([dune, atlas], marked="{'/b/Dune.epub': true, '/b/Atlas.pdf': true}", highlighted=dune) \
        == {"status": "2 Books marked", "enter": "Send 2 Books"}


def test_one_marked_book_is_singular():
    dune, atlas = book(path="/b/Dune.epub"), book(path="/b/Atlas.pdf", name="Atlas.pdf")

    assert footer([dune, atlas], marked="{'/b/Dune.epub': true}", highlighted=atlas) \
        == {"status": "1 Book marked", "enter": "Send 1 Book"}


def test_marked_books_their_route_cant_take_are_warned_about_before_enter():
    """They are still sent and fail with their reason (spec §5 rule 3)."""
    dune = book(path="/b/Dune.epub", usbOk=False)
    atlas = book(path="/b/Atlas.pdf", name="Atlas.pdf")

    result = footer([dune, atlas], marked="{'/b/Dune.epub': true, '/b/Atlas.pdf': true}",
                    overrides="{'/b/Dune.epub': 'usb'}", highlighted=atlas)

    assert result == {"status": "2 Books marked · USB can't take 1", "enter": "Send 2 Books"}


def test_both_routes_refusing_are_both_named():
    mobi = book(path="/b/Old.mobi", name="Old.mobi", route="usb", emailOk=False)
    docx = book(path="/b/Notes.docx", name="Notes.docx", usbOk=False)

    result = footer([mobi, docx], marked="{'/b/Old.mobi': true, '/b/Notes.docx': true}",
                    overrides="{'/b/Old.mobi': 'email', '/b/Notes.docx': 'usb'}")

    assert result["status"] == "2 Books marked · Email can't take 1 · USB can't take 1"


def test_on_the_waiting_line_with_nothing_marked_enter_sends_nothing():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert footer([book(path="/b/Dune.epub")], highlighted=waiting) == {"status": "", "enter": ""}


def test_with_no_rows_enter_sends_nothing():
    assert footer([]) == {"status": "", "enter": ""}


def test_hints_on_a_book_offer_mark_route_send_and_close():
    assert rows(f"hints({book(path='/b/Dune.epub')}, 'Send this Book', '', EN)") \
        == "Space  Mark      Tab  Route      Enter  Send this Book      Ctrl+,  Settings      Esc  Close"


def test_hints_on_the_waiting_line_offer_cancel_instead():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"hints({waiting}, '', '', EN)") == "Delete  Cancel waiting      Ctrl+,  Settings      Esc  Close"


def test_hints_with_marked_books_on_the_waiting_line_keep_send():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"hints({waiting}, 'Send 2 Books', '', EN)") \
        == "Delete  Cancel waiting      Enter  Send 2 Books      Ctrl+,  Settings      Esc  Close"


def test_hints_with_no_rows_offer_only_close():
    assert rows("hints(null, '', '', EN)") == "Ctrl+,  Settings      Esc  Close"


# --- The Picker's screens other than the list ------------------------------

def screen(**state):
    base = {"loading": False, "setupNeeded": False, "failure": "", "payloadCount": 0,
            "books": 1, "rows": 1, "filterText": "", "program": PROGRAM, "bookFolders": ["~/Books", "~/Downloads"]}
    return rows(f"screen({json.dumps({**base, **state})}, EN)")


def test_a_list_with_books_has_no_screen_of_its_own():
    assert screen() is None


def test_setup_needed_has_no_screen_of_its_own():
    """Settings cover the list while setup is needed; the old setup screen is gone."""
    assert screen(setupNeeded=True) is None


def test_no_books_in_the_folders_offers_settings_to_change_them():
    s = screen(books=0, rows=0)

    assert s["message"] == "No Books found in ~/Books, ~/Downloads"
    assert s["keys"] == "Enter  Change Book folders      Ctrl+,  Settings      Esc  Close"
    assert s["enter"] == "settings"
    assert s["field"] == "bookFolders"


def test_a_failed_listing_names_how_to_see_why_and_can_be_retried():
    s = screen(failure="failed", books=0, rows=0)

    assert s["message"] == "Couldn't list your Books."
    # The bundled kindle-send by its path: after a plain `omarchy plugin add` it isn't on PATH.
    assert s["detail"] == f"To see the error, run {PROGRAM} plan --folders in a terminal."
    assert s["keys"] == "Enter  Try again      Ctrl+,  Settings      Esc  Close"
    assert s["enter"] == "retry"


def test_a_slow_listing_can_be_retried():
    s = screen(failure="slow", books=0, rows=0)

    assert s["message"] == "Listing your Books took more than 10 seconds."
    assert s["detail"] == f"To see what's slow, run {PROGRAM} plan --folders in a terminal."
    assert s["enter"] == "retry"


def test_a_missing_program_means_a_broken_plugin_folder():
    """kindle-send ships inside the plugin folder (spec §17), so reinstalling the plugin brings it back."""
    s = screen(failure="missing", books=0, rows=0)

    assert s["message"] == "Couldn't run kindle-send."
    assert s["detail"] == f"{PROGRAM} is missing from the plugin folder. Reinstall Books to Kindle."
    assert s["keys"] == "Esc  Close"  # no kindle-send, so no Settings to open
    assert s["settings"] is False


def test_loading_names_what_it_is_doing_and_lets_you_type_ahead():
    folders = screen(loading=True, books=0, rows=0)
    files = screen(loading=True, books=0, rows=0, payloadCount=3)

    assert folders["message"] == "Looking for Books…"
    assert files["message"] == "Checking 3 files…"
    assert folders["typing"] is True


def test_no_matches_offers_to_clear_the_search():
    s = screen(rows=0, filterText="dune")

    assert s["message"] == "No matches for “dune”"
    assert s["keys"] == "Ctrl+,  Settings      Esc  Clear search"
    assert s["enter"] == "none"
    assert s["typing"] is True


def test_files_none_of_which_can_be_sent():
    s = screen(payloadCount=2, books=0, rows=0)

    assert s["message"] == "None of these files can be sent to a Kindle."
    assert s["keys"] == "Ctrl+,  Settings      Esc  Close"


def test_while_searching_esc_clears_the_search_first():
    assert rows(f"hints({book(path='/b/Dune.epub')}, 'Send this Book', 'du', EN)") \
        == "Space  Mark      Tab  Route      Enter  Send this Book      Ctrl+,  Settings      Esc  Clear search"


def test_a_waiting_book_keeps_the_list_even_with_no_other_books():
    """The waiting line is where Delete cancels it, so it must stay visible."""
    assert screen(books=0, rows=0, waiting=1) is None
    assert screen(rows=0, filterText="zzz", waiting=1) is None


# --- Tab overrides --------------------------------------------------------

def test_a_route_switched_by_hand_says_so():
    """The automatic reason no longer applies, so the details line says it was switched."""
    text = rows(f"details({book(route='usb', routeReason='Too big for email (76 MB).')}, 'usb', {NOW}, EN)")
    switched = rows(f"details({book()}, 'usb', {NOW}, EN)")

    assert text == "EPUB · 1.2 MB · Too big for email (76 MB)."
    assert switched == "EPUB · 1.2 MB · switched to USB"


def test_plans_route_reason_reads_from_its_code():
    reason = {"routeReason": "Too big for email (76 MB).", "routeReasonCode": "route_too_big_for_email",
              "routeReasonValues": {"mb": 76.5}}
    tr = "LANG({'message.route_too_big_for_email': 'Zu groß für E-Mail (%1 MB).'})"

    assert rows(f"details({book(route='usb', **reason)}, 'usb', {NOW}, {tr})") \
        == "EPUB · 1,2 MB · Zu groß für E-Mail (76,5 MB)."


def test_a_route_reason_with_an_unknown_code_shows_plans_english():
    reason = {"routeReason": "Something new.", "routeReasonCode": "route_new", "routeReasonValues": {}}

    assert rows(f"details({book(route='usb', **reason)}, 'usb', {NOW}, EN)") == "EPUB · 1.2 MB · Something new."


@pytest.mark.parametrize("size, wanted", [(512, "512 B"), (48_000, "48 KB"), (1_200_000, "1.2 MB"),
                                          (76_000_000, "76.0 MB")])
def test_sizes(size, wanted):
    assert rows(f"size({size}, EN)") == wanted


def test_sizes_are_written_the_languages_way():
    assert rows("size(1200000, LANG({}))") == "1,2 MB"


@pytest.mark.parametrize("sent, wanted", [
    ("2026-11-05T11:59:30Z", "sent just now"),
    ("2026-11-05T11:59:00Z", "sent 1 min ago"),
    ("2026-11-05T11:15:00Z", "sent 45 min ago"),
    ("2026-11-05T11:00:00Z", "sent 1 h ago"),
    ("2026-11-05T09:00:00Z", "sent 3 h ago"),
    ("2026-11-04T11:00:00Z", "sent yesterday"),
    ("2026-11-01T11:00:00Z", "sent 4 days ago"),
    ("nonsense", ""),
])
def test_how_long_ago_a_book_was_sent(sent, wanted):
    assert rows(f"sentAgo('{sent}', {NOW}, EN)") == wanted


def test_counts_in_the_picker_are_plural_entries():
    tr = ("LANG({'rows.marked': {one: 'ein Buch markiert', other: '%1 Bücher markiert'},"
          " 'rows.sendCount': {one: 'Ein Buch senden', other: '%1 Bücher senden'}})")
    dune, atlas = book(path="/b/Dune.epub"), book(path="/b/Atlas.pdf", name="Atlas.pdf")

    assert rows(f"footer([{dune}, {atlas}], {{'/b/Dune.epub': true}}, {{}}, null, {tr})") \
        == {"status": "ein Buch markiert", "enter": "Ein Buch senden"}
    assert rows(f"footer([{dune}, {atlas}], {{'/b/Dune.epub': true, '/b/Atlas.pdf': true}}, {{}}, null, {tr})") \
        == {"status": "2 Bücher markiert", "enter": "2 Bücher senden"}


def test_key_names_stay_as_they_are_in_another_language():
    tr = "LANG({'keys.close': 'Schließen', 'keys.settings': 'Einstellungen'})"

    assert rows(f"hints(null, '', '', {tr})") == "Ctrl+,  Einstellungen      Esc  Schließen"


def test_tab_on_an_unmarked_book_switches_only_it():
    dune, atlas = book(path="/b/Dune.epub"), book(path="/b/Atlas.pdf", name="Atlas.pdf")

    assert rows(f"switchRoutes([{dune}, {atlas}], {{'/b/Atlas.pdf': true}}, {{}}, {dune})") \
        == {"/b/Dune.epub": "usb"}


def test_tab_on_a_marked_book_switches_every_marked_book_to_the_same_route():
    """They converge on the Route the highlighted Book switches to, rather than each flipping."""
    dune = book(path="/b/Dune.epub")
    atlas = book(path="/b/Atlas.pdf", name="Atlas.pdf")
    big = book(path="/b/Big.pdf", name="Big.pdf", route="usb")
    other = book(path="/b/Other.pdf", name="Other.pdf")

    result = rows(f"switchRoutes([{dune}, {atlas}, {big}, {other}],"
                  " {'/b/Dune.epub': true, '/b/Atlas.pdf': true, '/b/Big.pdf': true}, {}, " + dune + ")")

    assert result == {"/b/Dune.epub": "usb", "/b/Atlas.pdf": "usb", "/b/Big.pdf": "usb"}


def test_tab_on_the_waiting_line_changes_nothing():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"switchRoutes([{book(path='/b/Dune.epub')}], {{}}, {{'/b/Dune.epub': 'usb'}}, {waiting})") \
        == {"/b/Dune.epub": "usb"}


def test_settings_open_from_every_other_screen():
    assert screen(books=0, rows=0)["settings"] is True
    assert screen(failure="failed", books=0, rows=0)["settings"] is True
