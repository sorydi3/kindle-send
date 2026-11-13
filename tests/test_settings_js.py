"""plugin/Settings.js, run under node (skipped without node): the Settings form's decisions (spec §9)."""
import json

from qmljs import evaluate, needs_node

pytestmark = needs_node

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"

QT_KEY_COMMA = 0x2C
QT_CTRL = 0x04000000
QT_SHIFT = 0x02000000
QT_ALT = 0x08000000


def form(expr):
    return evaluate("Settings.js", expr)


def values(**fields):
    base = {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": "~/Books, ~/Downloads"}
    return json.dumps({**base, **fields})


# --- Opening ----------------------------------------------------------------

def test_ctrl_comma_opens_settings():
    assert form(f"opensSettings({QT_KEY_COMMA}, {QT_CTRL})") is True


def test_a_plain_comma_does_not_open_settings():
    """It still filters the Book list."""
    assert form(f"opensSettings({QT_KEY_COMMA}, 0)") is False
    assert form(f"opensSettings({QT_KEY_COMMA}, {QT_SHIFT})") is False


def test_alt_ctrl_comma_belongs_to_someone_else():
    assert form(f"opensSettings({QT_KEY_COMMA}, {QT_CTRL | QT_ALT})") is False


def test_the_form_shows_what_kindle_send_settings_printed():
    line = json.dumps({"kindleAddress": KINDLE, "senderAddress": SENDER,
                       "bookFolders": ["~/Books", "/srv/my books"], "appPasswordStored": True})

    assert form(f"fromSettings({line})") == {
        "kindleAddress": KINDLE, "senderAddress": SENDER, "appPassword": "", "bookFolders": "~/Books, /srv/my books"}


def test_the_form_starts_blank_when_settings_gave_nothing():
    assert form("fromSettings(null)") == {"kindleAddress": "", "senderAddress": "", "appPassword": "",
                                          "bookFolders": ""}


def test_the_fields_in_order_with_their_help_lines():
    assert form("fields().map(function(f) { return [f.key, f.label, f.help] })") == [
        ["kindleAddress", "Kindle address", "Find it at amazon.com → Manage Your Content and Devices → Devices."],
        ["senderAddress", "Gmail address", "Amazon must list it as an approved sender, or it drops every Book."],
        ["appPassword", "Gmail app password",
         "Create one at myaccount.google.com/apppasswords. It needs 2-Step Verification."],
        ["bookFolders", "Book folders", "The folders the Picker lists, separated by commas."],
    ]


# --- Saving -----------------------------------------------------------------

def test_save_sends_the_book_folders_as_a_list():
    assert form(f"toSave({values(bookFolders=' ~/Books ,, /srv/my books ')})") == {
        "kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": ["~/Books", "/srv/my books"]}


def test_save_never_sends_a_password_it_was_not_given():
    assert "appPassword" not in form(f"toSave({values()})")
    assert "appPassword" not in form(f"toSave({values(appPassword='')})")


def test_save_sends_a_typed_password():
    assert form(f"toSave({values(appPassword='abcd efgh ijkl mnop')})")["appPassword"] == "abcd efgh ijkl mnop"


# --- The app password -----------------------------------------------------------

def password_field():
    return "fields().filter(function(f) { return f.key === 'appPassword' })[0]"


def test_only_the_app_password_field_is_masked():
    assert form("fields().filter(function(f) { return f.masked }).map(function(f) { return f.key })") \
        == ["appPassword"]


def test_the_password_field_says_a_stored_password_is_kept_until_one_is_typed():
    assert form(f"placeholder({password_field()}, true)") == "Stored. Type to replace it."
    assert form(f"placeholder({password_field()}, false)") == "xxxx xxxx xxxx xxxx"
    assert form("placeholder(fields()[0], true)") == "…@kindle.com"


def test_the_form_never_shows_the_password_even_when_one_is_stored():
    line = json.dumps({"kindleAddress": KINDLE, "senderAddress": SENDER, "appPasswordStored": True})

    assert form(f"fromSettings({line})")["appPassword"] == ""


def test_typing_a_password_is_an_edit():
    assert form(f"changed({values(appPassword='x')}, {values(appPassword='')})") is True


def test_saving_a_typed_password_checks_it_with_gmail():
    assert form(f"savingStatus({values(appPassword='abcd')})") \
        == "Checking the app password with Gmail…"


def test_saving_a_changed_gmail_address_without_a_typed_password_just_saves():
    assert form(f"savingStatus({values(senderAddress='new@gmail.com ')})") == "Saving…"


def test_saving_with_the_same_address_and_no_typed_password_just_saves():
    assert form(f"savingStatus({values(kindleAddress='new@kindle.com', senderAddress=' ' + SENDER)})") \
        == "Saving…"


def problems(*items):
    return json.dumps([{"field": f, "message": m, "blocking": b} for f, m, b in items])


def test_problems_are_shown_per_field():
    shown = form("byField(" + problems(("senderAddress", "That isn't an email address.", True),
                                       ("bookFolders", "~/Bokos doesn't exist, so the Picker skips it", False)) + ")")

    assert shown == {"senderAddress": "That isn't an email address.",
                     "bookFolders": "~/Bokos doesn't exist, so the Picker skips it"}


def test_a_problem_replaces_the_help_line():
    field = "fields()[1]"
    shown = json.dumps({"senderAddress": "That isn't an email address."})

    assert form(f"helpLine({field}, {shown})") == {"text": "That isn't an email address.", "problem": True}
    assert form(f"helpLine({field}, {{}})") == {
        "text": "Amazon must list it as an approved sender, or it drops every Book.", "problem": False}


def test_focus_goes_to_the_first_problem_in_form_order():
    found = problems(("bookFolders", "x", False), ("senderAddress", "y", True))

    assert form(f"firstProblem({found})") == "senderAddress"


def test_no_problem_leaves_focus_where_it_is():
    assert form("firstProblem([])") == ""
    assert form("firstProblem(" + problems(("", "shell.json isn't valid JSON", True)) + ")") == ""


def test_editing_a_field_clears_only_its_problem():
    shown = json.dumps({"kindleAddress": "a", "senderAddress": "b"})

    assert form(f"edited({shown}, 'senderAddress')") == {"kindleAddress": "a"}


def test_the_status_line_counts_the_values_that_need_fixing():
    one = problems(("kindleAddress", "That isn't an email address.", True))
    two = problems(("kindleAddress", "That isn't an email address.", True),
                   ("senderAddress", "That isn't an email address.", True))

    assert form(f"status({{saved: false, problems: {one}}})") == "1 value needs fixing"
    assert form(f"status({{saved: false, problems: {two}}})") == "2 values need fixing"


def test_a_problem_with_the_whole_form_is_the_status_line():
    found = problems(("", "/home/x/.config/omarchy/shell.json isn't valid JSON, so it wasn't changed.", True))

    assert form(f"status({{saved: false, problems: {found}}})") \
        == "/home/x/.config/omarchy/shell.json isn't valid JSON, so it wasn't changed."


def test_saved_says_so_and_counts_the_warnings():
    found = problems(("kindleAddress", "Kindle addresses usually end in @kindle.com", False))

    assert form("status({saved: true, problems: []})") == "Saved."
    assert form(f"status({{saved: true, problems: {found}}})") == "Saved. 1 value to check below."


def test_the_status_line_is_empty_before_saving():
    assert form("status(null)") == ""


# --- Leaving and the footer ---------------------------------------------------

def test_unchanged_values_are_not_edits():
    assert form(f"changed({values()}, {values()})") is False


def test_any_changed_field_is_an_edit():
    assert form(f"changed({values(bookFolders='~/Books')}, {values()})") is True


def test_the_footer_offers_tab_save_and_back():
    assert form("footer('', false)") == "Tab  Next field      Enter  Save      Esc  Back to Books"


def test_the_footer_warns_that_esc_discards_once_something_changed():
    assert form("footer('', true)") \
        == "Tab  Next field      Enter  Save      Esc  Back (discard changes)"


# --- Help links (spec §9, Links) -------------------------------------------------

QT_KEY_O = 0x4F

MANAGE_DEVICES = "https://www.amazon.com/mycd"
APPROVED_LIST = "https://www.amazon.com/hz/mycd/myx#/home/settings/pdoc"
APP_PASSWORDS = "https://myaccount.google.com/apppasswords"


def test_each_address_field_links_to_where_its_value_comes_from():
    assert form("link('kindleAddress')") == MANAGE_DEVICES
    assert form("link('senderAddress')") == APPROVED_LIST


def test_the_app_password_links_to_googles_app_passwords_page():
    assert form("link('appPassword')") == APP_PASSWORDS


def test_book_folders_have_no_link():
    """They get Browse instead."""
    assert form("link('bookFolders')") == ""
    assert form("link('')") == ""


def test_the_footer_offers_open_link_on_a_field_with_a_link():
    assert form("footer('senderAddress', false)") \
        == "Tab  Next field      Enter  Save      Ctrl+O  Open link      Esc  Back to Books"


def test_the_footer_never_offers_open_link_where_there_is_none():
    assert "Open link" not in form("footer('bookFolders', true)")
    assert "Open link" not in form("footer('', false)")


def test_ctrl_o_opens_the_link():
    assert form(f"opensLink({QT_KEY_O}, {QT_CTRL})") is True


def test_a_plain_or_shifted_o_is_typing():
    assert form(f"opensLink({QT_KEY_O}, 0)") is False
    assert form(f"opensLink({QT_KEY_O}, {QT_SHIFT})") is False
    assert form(f"opensLink({QT_KEY_O}, {QT_CTRL | QT_SHIFT})") is False


def test_the_link_opens_in_the_browser_omarchy_launches():
    assert form("browserArgv('senderAddress')") == ["omarchy-launch-browser", APPROVED_LIST]


def test_nothing_is_launched_for_a_field_without_a_link():
    assert form("browserArgv('bookFolders')") == []


# --- Stepping aside (for a link, or Browse) and coming back ---------------------

def test_reopening_after_stepping_aside_returns_to_settings_with_unsaved_values():
    typed = values(kindleAddress="new@kindle.com")
    open_form = ("{values: " + typed + ", baseline: " + values() + ", focus: 'kindleAddress',"
                 " problems: {senderAddress: 'Make sure this is a Google account'}, status: 'Saved.'}")

    back = form(f"reopened(stepAside({open_form}))")

    assert back["values"]["kindleAddress"] == "new@kindle.com"
    assert back["baseline"]["kindleAddress"] == KINDLE
    assert back["focus"] == "kindleAddress"
    assert back["problems"] == {"senderAddress": "Make sure this is a Google account"}
    assert back["status"] == "Saved."
    assert form(f"(function(b) {{ return changed(b.values, b.baseline) }})(reopened(stepAside({open_form})))") is True


def test_the_kept_form_does_not_follow_later_edits():
    """What comes back is what was there when the Picker stepped aside."""
    expr = ("(function() { var f = {values: {kindleAddress: 'a@kindle.com'}};"
            " var kept = stepAside(f); f.values.kindleAddress = 'b@kindle.com';"
            " return reopened(kept).values.kindleAddress })()")

    assert form(expr) == "a@kindle.com"


def test_an_ordinary_open_starts_in_the_book_list():
    assert form("reopened(null)") is None


# --- Browse for a Book folder (spec §9, Book folders) -------------------------

QT_KEY_B = 0x42
HOME = "/home/reader"


def test_the_footer_offers_browse_on_book_folders():
    assert form("footer('bookFolders', false)") \
        == "Tab  Next field      Enter  Save      Ctrl+B  Browse      Esc  Back to Books"


def test_the_footer_offers_browse_only_on_book_folders():
    for key in ("kindleAddress", "senderAddress", "appPassword", ""):
        assert "Browse" not in form(f"footer('{key}', false)")


def test_ctrl_b_browses():
    assert form(f"opensBrowse({QT_KEY_B}, {QT_CTRL})") is True


def test_a_plain_or_shifted_b_is_typing():
    assert form(f"opensBrowse({QT_KEY_B}, 0)") is False
    assert form(f"opensBrowse({QT_KEY_B}, {QT_SHIFT})") is False
    assert form(f"opensBrowse({QT_KEY_B}, {QT_CTRL | QT_ALT})") is False


def test_a_folder_inside_home_is_written_with_a_tilde():
    assert form(f"chosenFolder('file://{HOME}/Documents/Kindle books', '{HOME}')") == "~/Documents/Kindle books"


def test_the_chooser_url_is_decoded():
    assert form(f"chosenFolder('file://{HOME}/My%20Books/%C3%89pub', '{HOME}')") == "~/My Books/Épub"


def test_home_itself_is_a_tilde():
    assert form(f"chosenFolder('file://{HOME}', '{HOME}')") == "~"
    assert form(f"chosenFolder('file://{HOME}/', '{HOME}/')") == "~"


def test_a_folder_outside_home_keeps_its_full_path():
    assert form(f"chosenFolder('file:///srv/library/books', '{HOME}')") == "/srv/library/books"


def test_a_neighbour_of_home_is_not_inside_it():
    assert form(f"chosenFolder('file://{HOME}2/Books', '{HOME}')") == f"{HOME}2/Books"


def test_without_a_home_the_full_path_is_kept():
    assert form(f"chosenFolder('file://{HOME}/Books', '')") == f"{HOME}/Books"


def test_a_picked_folder_is_appended_to_the_field():
    assert form("withFolder('~/Books, ~/Downloads', '~/Papers')") == "~/Books, ~/Downloads, ~/Papers"


def test_a_picked_folder_fills_an_empty_field():
    assert form("withFolder('', '~/Papers')") == "~/Papers"
    assert form("withFolder('  ', '~/Papers')") == "~/Papers"


def test_a_trailing_comma_does_not_leave_an_empty_entry():
    assert form("withFolder('~/Books, ', '~/Papers')") == "~/Books, ~/Papers"


def test_a_folder_already_listed_is_not_added_twice():
    assert form("withFolder('~/Books, ~/Papers', '~/Papers')") == "~/Books, ~/Papers"


def test_cancel_adds_nothing():
    """FolderDialog's reject gives no folder."""
    assert form("withFolder('~/Books', '')") == "~/Books"


def test_browsing_into_the_form_keeps_the_other_unsaved_values_and_marks_an_edit():
    expr = ("(function() { var kept = stepAside({values: " + values(kindleAddress="new@kindle.com")
            + ", baseline: " + values() + "}); var back = reopened(kept);"
            " back.values.bookFolders = withFolder(back.values.bookFolders,"
            f" chosenFolder('file://{HOME}/Papers', '{HOME}'));"
            " return [back.values, changed(back.values, back.baseline)] })()")

    got, edited = form(expr)
    assert got["kindleAddress"] == "new@kindle.com"
    assert got["bookFolders"] == "~/Books, ~/Downloads, ~/Papers"
    assert edited is True


# --- Setup needed (spec §4, §9) -------------------------------------------------

def test_while_something_is_missing_the_form_is_titled_set_up():
    assert form("title(['appPassword'])") == "Set up Send to Kindle"


def test_once_nothing_is_missing_the_form_is_titled_settings():
    assert form("title([])") == "Settings"


def test_settings_says_what_is_missing():
    line = json.dumps({"kindleAddress": "", "missing": ["kindleAddress", "appPassword"]})

    assert form(f"missing({line})") == ["kindleAddress", "appPassword"]
    assert form("missing(null)") == []


def flag(key, missing, typed=None):
    blank = values(kindleAddress="", appPassword="")
    now = values(**{"kindleAddress": "", "appPassword": "", **(typed or {})})
    return form(f"flag('{key}', {json.dumps(missing)}, {now}, {blank})")


def test_a_missing_value_is_flagged_needed():
    assert flag("kindleAddress", ["kindleAddress", "appPassword"]) == "· needed"
    assert flag("appPassword", ["kindleAddress", "appPassword"]) == "· needed"


def test_a_value_that_is_set_has_no_flag():
    assert flag("senderAddress", ["kindleAddress", "appPassword"]) == ""


def test_while_setup_is_needed_esc_closes_the_picker():
    """There is no usable Book list to go back to yet."""
    assert form("escCloses(['appPassword'])") is True
    assert form("footer('kindleAddress', false, true)") \
        == "Tab  Next field      Enter  Save      Ctrl+O  Open link      Esc  Close"


def test_while_setup_is_needed_esc_closes_even_after_edits():
    assert form("footer('bookFolders', true, true)") \
        == "Tab  Next field      Enter  Save      Ctrl+B  Browse      Esc  Close"


def test_once_set_up_esc_goes_back_to_books():
    assert form("escCloses([])") is False
    assert form("footer('bookFolders', false, false)").endswith("Esc  Back to Books")


def needed(field):
    return {"field": field, "message": "Needed before Books can be sent.", "blocking": True, "needed": True}


def test_saving_with_values_missing_says_how_many_are_still_needed():
    one = json.dumps([needed("appPassword")])
    three = json.dumps([needed("kindleAddress"), needed("senderAddress"), needed("appPassword")])

    assert form(f"status({{saved: false, problems: {one}}})") == "1 still needed before Books can be sent."
    assert form(f"status({{saved: false, problems: {three}}})") == "3 still needed before Books can be sent."


def test_missing_values_are_counted_even_beside_one_that_needs_fixing():
    found = json.dumps([needed("kindleAddress"),
                        {"field": "senderAddress", "message": "That isn't an email address.", "blocking": True}])

    assert form(f"status({{saved: false, problems: {found}}})") == "1 still needed before Books can be sent."


def test_the_flag_clears_as_soon_as_the_field_is_edited():
    assert flag("kindleAddress", ["kindleAddress"], {"kindleAddress": "r"}) == ""
    assert flag("appPassword", ["appPassword"], {"appPassword": "a"}) == ""


# --- Opening from a failure notification (spec §10, §13) ---------------------

def summoned(payload):
    return form(f"summoned({json.dumps(json.dumps(payload))})")


def test_a_rejected_password_opens_on_the_password_with_the_problem_shown():
    opened = summoned({"settings": "appPassword", "problem": "Gmail rejected the app password."})

    assert opened == {"focus": "appPassword", "problems": {"appPassword": "Gmail rejected the app password."}}


def test_a_missing_password_opens_on_the_password_saying_so():
    opened = summoned({"settings": "appPassword", "problem": "No app password stored."})

    assert opened == {"focus": "appPassword", "problems": {"appPassword": "No app password stored."}}


def test_a_missing_setting_opens_on_that_field_flagged_as_needed():
    opened = summoned({"settings": "senderAddress", "problem": "Not set up: senderAddress missing."})

    assert opened == {"focus": "senderAddress", "problems": {"senderAddress": "Needed before Books can be sent."}}


def test_the_problem_shows_in_place_of_the_fields_help():
    opened = summoned({"settings": "kindleAddress", "problem": "Not set up: kindleAddress missing."})
    expr = f"helpLine(fields()[0], {json.dumps(opened['problems'])})"

    assert form(expr) == {"text": "Needed before Books can be sent.", "problem": True}


def test_other_summons_do_not_open_settings_on_a_field():
    assert summoned({}) is None
    assert summoned({"files": ["/b/Dune.epub"]}) is None
    assert summoned({"settings": "maxEmailsPerHour", "problem": "x"}) is None
    assert summoned({"settings": "bookFolders", "problem": "x"}) is None
    assert form('summoned("not json")') is None
    assert form('summoned("")') is None


def from_menu(payload):
    return form(f"opensFromMenu({json.dumps(json.dumps(payload))})")


def test_the_menus_settings_entry_opens_settings_on_no_field():
    assert from_menu({"settings": ""}) is True


def test_other_summons_are_not_the_menus_settings_entry():
    assert from_menu({}) is False
    assert from_menu({"files": ["/b/Dune.epub"]}) is False
    assert from_menu({"settings": "appPassword", "problem": "x"}) is False
    assert form('opensFromMenu("not json")') is False
    assert form('opensFromMenu("")') is False


# --- Test send (spec §9) --------------------------------------------------------

QT_KEY_T = 0x54
SUGGESTION = "Ctrl+T sends a test Book to check it all works."


def test_the_first_save_suggests_the_test_send():
    assert form("status({saved: true, firstSave: true, problems: []})") == "Saved. " + SUGGESTION


def test_a_first_save_with_warnings_names_them_before_the_suggestion():
    found = json.dumps([{"field": "kindleAddress", "message": "Kindle addresses usually end in @kindle.com",
                         "blocking": False}])

    assert form(f"status({{saved: true, firstSave: true, problems: {found}}})") \
        == "Saved. 1 value to check below. " + SUGGESTION


def test_later_saves_do_not_suggest_the_test_send():
    assert form("status({saved: true, problems: []})") == "Saved."


def test_ctrl_t_is_the_test_send_key():
    assert form(f"opensTestSend({QT_KEY_T}, {QT_CTRL})") is True
    assert form(f"opensTestSend({QT_KEY_T}, 0)") is False
    assert form(f"opensTestSend({QT_KEY_T}, {QT_CTRL | QT_SHIFT})") is False
    assert form(f"opensTestSend({QT_KEY_COMMA}, {QT_CTRL})") is False


def test_ctrl_t_sends_only_once_everything_is_saved():
    # testKey(isSetup, isChanged, testSend)
    assert form("testKey(false, false, null)") == {"send": True, "status": ""}
    assert form("testKey(false, false, {state: 'sent', at: 1})")["send"] is True
    assert form("testKey(false, true, null)") == {"send": False, "status": "Save first, then Ctrl+T sends a test Book."}
    assert form("testKey(true, false, null)") == {"send": False, "status": "Save first, then Ctrl+T sends a test Book."}


def test_ctrl_t_while_the_test_book_is_going_does_nothing_more():
    assert form("testKey(false, false, {state: 'sending'})") == {"send": False, "status": "Sending a test Book…"}


def test_the_status_line_follows_the_test_send():
    assert form("testOutcome({state: 'sending'})") == {"status": "Sending a test Book…", "problems": {}}
    sent = form("testOutcome({state: 'sent', at: new Date(2026, 10, 13, 9, 5).getTime()})")
    assert sent == {"status": "Gmail accepted the test Book at 09:05. Check your Kindle in a few minutes.",
                    "problems": {}}


def test_a_failed_test_send_shows_next_to_its_field():
    failed = form("testOutcome({state: 'failed', at: 1, reason: 'Gmail rejected the app password.', "
                  "field: 'appPassword'})")

    assert failed == {"status": "Couldn't send the test Book.",
                      "problems": {"appPassword": "Gmail rejected the app password."}}


def test_a_failed_test_send_no_field_fixes_is_the_status_line():
    failed = form("testOutcome({state: 'failed', at: 1, reason: 'Couldn\\'t reach Gmail.', field: ''})")

    assert failed == {"status": "Couldn't send the test Book. Couldn't reach Gmail.", "problems": {}}
