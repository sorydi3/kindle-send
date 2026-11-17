"""Catalog.js, run under node (skipped without node): the plugin's text from
its English catalog, i18n/en.json (spec §17, Translations).

Every text function of the plugin's JS takes a translator `tr` ({t, tn, num}):
the Picker and the Service hand in Omarchy's Commons.Translations and
Commons.I18n.formatNumber; these tests hand in EN, the same lookups over
i18n/en.json, or LANG({...}), a made-up language over it that writes numbers
with a decimal comma (tests/qmljs.py).
"""
import json
from pathlib import Path

import pytest

from qmljs import evaluate, needs_node
from test_message_codes import CODES, EXAMPLE

pytestmark = needs_node

CATALOG = json.loads((Path(__file__).resolve().parent.parent / "i18n" / "en.json").read_text())


def cat(expr):
    return evaluate("Catalog.js", expr)


def test_a_known_code_reads_its_catalog_text():
    assert cat("message(EN, 'too_big_for_email', {mb: 76}, 'english')") \
        == "Too big for email (76 MB). Switch it to USB."


def test_an_unknown_code_falls_back_to_the_english_text_kindle_send_sent():
    assert cat("message(EN, 'brand_new_code', {x: 1}, 'Something new went wrong.')") \
        == "Something new went wrong."


def test_without_a_code_the_english_text_shows():
    assert cat("message(EN, '', {}, 'target is busy')") == "target is busy"
    assert cat("message(EN, undefined, undefined, 'target is busy')") == "target is busy"
    assert cat("message(EN, undefined, undefined, undefined)") == ""


def test_another_language_is_used_where_it_has_the_code():
    assert cat("message(LANG({'message.too_big_for_email': 'Zu groß (%1 MB).'}), 'too_big_for_email',"
               " {mb: 7.5}, 'english')") == "Zu groß (7,5 MB)."


def test_sizes_go_through_the_number_formatter():
    assert cat("message(LANG({}), 'kindle_full', {mb: 12.5}, 'x')") \
        == "Not enough space on the Kindle (needs 12,5 MB)."


def test_system_detail_text_is_inserted_as_it_is():
    assert cat("message(EN, 'gmail_unreachable', {detail: 'timed out %1'}, 'x')") \
        == "Couldn't reach Gmail: timed out %1."


def test_missing_fields_are_named_by_their_labels_joined_with_and():
    assert cat("message(EN, 'not_set_up', {fields: ['kindleAddress']}, 'x')") \
        == "Not set up: Kindle address missing."
    assert cat("message(EN, 'not_set_up', {fields: ['kindleAddress', 'senderAddress', 'appPassword']}, 'x')") \
        == "Not set up: Kindle address, Gmail address and Gmail app password missing."


def test_folder_lists_are_joined_with_and():
    assert cat("message(EN, 'book_folders_missing', {folders: ['~/Bokos', '/nowhere']}, 'x')") \
        == "~/Bokos and /nowhere don't exist, so the Picker skips them."


def test_every_code_kindle_send_sends_has_catalog_text_using_all_its_values():
    for code, names in CODES.items():
        text = CATALOG.get("message." + code)
        assert isinstance(text, str) and text, code
        for n in range(1, len(names) + 1):
            assert f"%{n}" in text, (code, text)
        assert f"%{len(names) + 1}" not in text, (code, text)
        assert sorted(cat(f"ORDER[{json.dumps(code)}] || []")) == sorted(names), code


def test_every_code_reads_as_the_english_kindle_send_sends(ks):
    for code, names in CODES.items():
        if code == "not_set_up":
            continue  # kindle-send names field keys there; the plugin names their labels
        values = {name: EXAMPLE[name] for name in names}
        english = ks.MESSAGES[code](values)
        assert cat(f"message(EN, {json.dumps(code)}, {json.dumps(values)}, '')") == english, code


def test_placeholders_fill_in_order_and_leave_the_rest_alone():
    assert cat("fill('%2 of %1, 100%', [3, 1])") == "1 of 3, 100%"
    assert cat("fill('%1', ['%2', 'x'])") == "%2"


@pytest.mark.parametrize("n, wanted", [(1, "1 Book"), (2, "2 Books"), (0, "0 Books"), (1000, "1000 Books")])
def test_counts_read_their_plural_entry_and_format_the_number(n, wanted):
    assert cat(f"count(LANG({{'x.books': {{one: '%1 Book', other: '%1 Books'}}}}), 'x.books', {n})") == wanted


def test_every_catalog_entry_is_a_string_or_an_english_plural():
    for key, value in CATALOG.items():
        if isinstance(value, dict):
            assert set(value) == {"one", "other"}, key
            assert all(isinstance(v, str) and v for v in value.values()), key
        else:
            assert isinstance(value, str) and value, key
