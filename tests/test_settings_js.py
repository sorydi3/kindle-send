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
    assert form(f"savingStatus({values(appPassword='abcd')}, {values(appPassword='')})") \
        == "Checking the app password with Gmail…"


def test_saving_a_changed_gmail_address_checks_the_password_with_gmail():
    assert form(f"savingStatus({values(senderAddress='new@gmail.com ')}, {values()})") \
        == "Checking the app password with Gmail…"


def test_saving_with_the_same_address_and_no_typed_password_just_saves():
    assert form(f"savingStatus({values(kindleAddress='new@kindle.com', senderAddress=' ' + SENDER)}, {values()})") \
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
    one = problems(("kindleAddress", "Needed before Books can be sent.", True))
    two = problems(("kindleAddress", "Needed before Books can be sent.", True),
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
