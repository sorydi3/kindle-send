"""Rows.js, run under node (skipped without node): the Picker's row text."""
import json

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
    text = rows(f"details({book(lastSent='2026-11-02T11:00:00+00:00')}, 'email', {NOW})")

    assert text == "EPUB · 1.2 MB · sent 3 days ago"


def test_a_book_sent_yesterday():
    assert rows(f"details({book(lastSent='2026-11-04T09:00:00+00:00')}, 'email', {NOW})") \
        == "EPUB · 1.2 MB · sent yesterday"


def test_a_book_never_sent_has_no_mark():
    assert rows(f"details({book()}, 'email', {NOW})") == "EPUB · 1.2 MB"


def test_an_already_sent_book_is_sent_again_like_any_other():
    """Re-sending needs no confirmation: marking a sent Book sends it."""
    chosen = rows(f"toSend([{book(path='/b/Dune.epub', lastSent='2026-11-02T11:00:00+00:00')}],"
                  " {'/b/Dune.epub': true}, {}, 0)")

    assert chosen == [{"path": "/b/Dune.epub", "name": "Dune.epub", "route": "email"}]


def test_enter_on_the_waiting_line_sends_nothing():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"toSend([{book(path='/b/Dune.epub')}], {{}}, {{}}, {waiting})") == []


def test_a_plan_that_needs_setup_sends_the_picker_into_settings():
    """The Picker then opens straight into Settings, titled "Set up Send to Kindle" (spec §4, §9)."""
    parsed = rows("fromPlan([{setupNeeded: true, missing: ['appPassword']},"
                  f" {book(path='/b/Dune.epub')}])")

    assert parsed["setupNeeded"] is True
    assert parsed["missing"] == ["appPassword"]


def test_a_plan_without_setup_needed_lists_books():
    parsed = rows(f"fromPlan([{book(path='/b/Dune.epub')}])")

    assert parsed["setupNeeded"] is False
    assert [b["path"] for b in parsed["books"]] == ["/b/Dune.epub"]


LABELS = json.dumps({"email": "Email", "usb": "USB"})


def test_plan_info_gives_the_book_folders_and_route_labels():
    parsed = rows("fromPlan([{bookFolders: ['~/Library'], routeLabels: {email: 'Email', usb: 'USB'}},"
                  f" {book(path='/b/Dune.epub')}])")

    assert parsed["bookFolders"] == ["~/Library"]
    assert parsed["routeLabels"] == {"email": "Email", "usb": "USB"}
    assert [b["path"] for b in parsed["books"]] == ["/b/Dune.epub"]


def test_without_plan_info_the_empty_state_names_no_folders():
    assert rows("fromPlan([])")["bookFolders"] == []
    assert rows("emptyMessage([])") == "No Books found in your Book folders"


def test_route_labels_come_from_plan():
    assert rows(f"routeLabel('usb', {LABELS})") == "USB"


def test_a_route_the_book_cant_take_is_named_in_details():
    text = rows(f"details({book(usbOk=False)}, 'usb', {NOW}, {LABELS})")

    assert text == "EPUB · 1.2 MB · USB can't take this Book"


def test_tab_switches_between_the_two_routes():
    assert rows("[switchRoute('email'), switchRoute('usb')]") == ["usb", "email"]


# --- What Enter will send, said in the footer -----------------------------

def footer(books, marked="{}", overrides="{}", highlighted="null"):
    return rows(f"footer([{', '.join(books)}], {marked}, {overrides}, {highlighted}, {LABELS})")


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
    assert rows(f"hints({book(path='/b/Dune.epub')}, 'Send this Book')") \
        == "Space  Mark      Tab  Route      Enter  Send this Book      Ctrl+,  Settings      Esc  Close"


def test_hints_on_the_waiting_line_offer_cancel_instead():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"hints({waiting}, '')") == "Delete  Cancel waiting      Ctrl+,  Settings      Esc  Close"


def test_hints_with_marked_books_on_the_waiting_line_keep_send():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"hints({waiting}, 'Send 2 Books')") \
        == "Delete  Cancel waiting      Enter  Send 2 Books      Ctrl+,  Settings      Esc  Close"


def test_hints_with_no_rows_offer_only_close():
    assert rows("hints(null, '')") == "Ctrl+,  Settings      Esc  Close"


# --- The Picker's screens other than the list ------------------------------

def screen(**state):
    base = {"loading": False, "setupNeeded": False, "failure": "", "payloadCount": 0,
            "books": 1, "rows": 1, "filterText": "", "bookFolders": ["~/Books", "~/Downloads"]}
    return rows(f"screen({json.dumps({**base, **state})})")


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
    assert s["detail"] == "To see the error, run kindle-send plan --folders in a terminal."
    assert s["keys"] == "Enter  Try again      Ctrl+,  Settings      Esc  Close"
    assert s["enter"] == "retry"


def test_a_slow_listing_can_be_retried():
    s = screen(failure="slow", books=0, rows=0)

    assert s["message"] == "Listing your Books took more than 10 seconds."
    assert s["enter"] == "retry"


def test_a_missing_program_says_how_to_install_it():
    s = screen(failure="missing", books=0, rows=0)

    assert s["message"] == "kindle-send isn't installed."
    assert s["detail"] == "Run scripts/install.sh from the kindle-send folder."
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
    assert rows(f"hints({book(path='/b/Dune.epub')}, 'Send this Book', 'du')") \
        == "Space  Mark      Tab  Route      Enter  Send this Book      Ctrl+,  Settings      Esc  Clear search"


def test_a_waiting_book_keeps_the_list_even_with_no_other_books():
    """The waiting line is where Delete cancels it, so it must stay visible."""
    assert screen(books=0, rows=0, waiting=1) is None
    assert screen(rows=0, filterText="zzz", waiting=1) is None


# --- Tab overrides --------------------------------------------------------

def test_a_route_switched_by_hand_says_so():
    """The automatic reason no longer applies, so the details line says it was switched."""
    text = rows(f"details({book(route='usb', routeReason='Too big for email (76 MB).')}, 'usb', {NOW}, {LABELS})")
    switched = rows(f"details({book()}, 'usb', {NOW}, {LABELS})")

    assert text == "EPUB · 1.2 MB · Too big for email (76 MB)."
    assert switched == "EPUB · 1.2 MB · switched to USB"


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
