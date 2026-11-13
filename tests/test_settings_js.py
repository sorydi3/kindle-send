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
        "kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": "~/Books, /srv/my books"}


def test_the_form_starts_blank_when_settings_gave_nothing():
    assert form("fromSettings(null)") == {"kindleAddress": "", "senderAddress": "", "bookFolders": ""}


def test_the_fields_in_order_with_their_help_lines():
    assert form("fields().map(function(f) { return [f.key, f.label, f.help] })") == [
        ["kindleAddress", "Kindle address", "Find it at amazon.com → Manage Your Content and Devices → Devices."],
        ["senderAddress", "Gmail address", "Amazon must list it as an approved sender, or it drops every Book."],
        ["bookFolders", "Book folders", "The folders the Picker lists, separated by commas."],
    ]


# --- Saving -----------------------------------------------------------------

def test_save_sends_the_book_folders_as_a_list():
    assert form(f"toSave({values(bookFolders=' ~/Books ,, /srv/my books ')})") == {
        "kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": ["~/Books", "/srv/my books"]}


def test_save_never_sends_a_password_it_was_not_given():
    assert "appPassword" not in form(f"toSave({values()})")


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
    assert form("footer('kindleAddress', false)") == "Tab  Next field      Enter  Save      Esc  Back to Books"


def test_the_footer_warns_that_esc_discards_once_something_changed():
    assert form("footer('kindleAddress', true)") \
        == "Tab  Next field      Enter  Save      Esc  Back (discard changes)"
