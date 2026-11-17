"""The message codes kindle-send sends the shell (spec §17, Translations).

Every sentence the shell shows comes with a stable code and its values beside
the English text; the plugin's catalog (i18n/en.json) keys its text by these
codes. The per-message tests live with each command's tests; this file pins
the list itself, which the catalog must cover.
"""

# Renaming or dropping one breaks the plugin's catalog, so this list only grows.
CODES = {
    # Send failures: {"result": "failed", "code", "values", "reason"}
    "too_big_for_email": {"mb"},
    "format_not_emailable": {"format"},
    "format_not_for_usb": {"format"},
    "file_not_found": {"name"},
    "not_set_up": {"fields"},
    "no_app_password": set(),
    "password_rejected": set(),
    "gmail_unreachable": {"detail"},
    "kindle_not_plugged_in": set(),
    "kindle_full": {"mb"},
    "copy_failed": {"detail"},
    "calibre_missing": set(),
    "conversion_failed": {"detail"},
    "test_book_missing": set(),
    # plan rows: routeReason, routeReasonCode, routeReasonValues
    "route_format_not_emailable": {"format"},
    "route_too_big_for_email": {"mb"},
    # eject: {"ejected": false, "code", "values", "reason"}
    "eject_no_kindle": set(),
    "eject_failed": {"detail"},
    "eject_step_failed": {"step"},
    # save problems: {"field", "code", "values", "message", "blocking"}
    "value_needed": set(),
    "not_an_email_address": set(),
    "kindle_address_unusual": set(),
    "sender_not_gmail": set(),
    "book_folder_missing": {"folder"},
    "book_folders_missing": {"folders"},
    "app_password_rejected": set(),
    "password_check_unreachable": set(),
    "secret_tool_missing": set(),
    "password_not_stored": set(),
    "form_unreadable": set(),
    "settings_file_invalid": {"path"},
    "settings_file_unwritable": {"path", "detail"},
}

EXAMPLE = {"mb": 76, "format": "AZW3", "name": "Dune.epub", "fields": ["kindleAddress"],
           "detail": "timed out", "step": "unmount", "folder": "~/Bokos",
           "folders": ["~/Bokos", "/nowhere"], "path": "/home/me/.config/omarchy/shell.json"}


def test_the_codes_are_listed_in_one_place(ks):
    assert set(ks.MESSAGES) == set(CODES)


def test_each_code_turns_its_values_into_one_english_sentence(ks):
    for code, names in CODES.items():
        values = {name: EXAMPLE[name] for name in names}
        message = ks.said(code, **values)
        assert message["code"] == code
        assert message["values"] == values
        assert message["text"] and "{" not in message["text"], code


def test_the_spec_example(ks):
    assert ks.said("too_big_for_email", mb=76) == {
        "code": "too_big_for_email", "values": {"mb": 76},
        "text": "Too big for email (76 MB). Switch it to USB."}
