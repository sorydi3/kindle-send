"""`kindle-send limit`: when the next email may go, from the Send history (spec §3, §11)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from conftest import write_shell_json

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock(ks, monkeypatch):
    monkeypatch.setattr(ks, "now", lambda: NOW)


def ago(seconds):
    return (NOW - timedelta(seconds=seconds)).isoformat(timespec="seconds")


def write_history(home, *entries):
    state = home / ".local" / "state" / "kindle-send"
    state.mkdir(parents=True, exist_ok=True)
    (state / "history.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))


def sent(seconds_ago, route="email", result="sent", name="Dune.epub"):
    return {"time": ago(seconds_ago), "name": name, "size": 10, "route": route, "result": result}


def limit(ks, capsys):
    assert ks.main(["limit"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_with_no_history_an_email_may_go_now(ks, home, clock, capsys):
    assert limit(ks, capsys) == {"canSendIn": 0, "sentLastHour": 0, "maxEmailsPerHour": 20}


def test_an_email_sent_4_seconds_ago_means_waiting_6_more(ks, home, clock, capsys):
    write_history(home, sent(600), sent(4))

    result = limit(ks, capsys)

    assert (result["canSendIn"], result["sentLastHour"]) == (6, 2)


def test_failures_and_usb_copies_do_not_count(ks, home, clock, capsys):
    write_history(home, sent(30), sent(3, result="failed"), sent(2, route="usb", result="copied"))

    result = limit(ks, capsys)

    assert (result["canSendIn"], result["sentLastHour"]) == (0, 1)


def test_at_20_emails_in_the_hour_the_next_waits_for_the_oldest_to_age_out(ks, home, clock, capsys):
    # 20 sent over the last hour, oldest 50 minutes ago; one older than an hour.
    write_history(home, sent(4000), *[sent(3000 - i * 100) for i in range(20)])

    result = limit(ks, capsys)

    assert (result["canSendIn"], result["sentLastHour"]) == (600, 20)


def test_under_the_cap_only_the_gap_applies(ks, home, clock, capsys):
    write_history(home, *[sent(3000 - i * 100) for i in range(19)])

    assert limit(ks, capsys)["canSendIn"] == 0


def test_both_numbers_come_from_settings(ks, home, clock, capsys):
    write_shell_json(home, minEmailGapSeconds=60, maxEmailsPerHour=2)
    write_history(home, sent(1800), sent(20))

    assert limit(ks, capsys) == {"canSendIn": 1800, "sentLastHour": 2, "maxEmailsPerHour": 2}


def test_a_gap_setting_alone_still_applies(ks, home, clock, capsys):
    write_shell_json(home, minEmailGapSeconds=60)
    write_history(home, sent(20))

    assert limit(ks, capsys) == {"canSendIn": 40, "sentLastHour": 1, "maxEmailsPerHour": 20}


@pytest.mark.parametrize("bad", ["ten", None, -5, True])
def test_unusable_settings_fall_back_to_the_defaults(ks, home, clock, capsys, bad):
    write_shell_json(home, minEmailGapSeconds=bad, maxEmailsPerHour=bad)
    write_history(home, sent(4))

    assert limit(ks, capsys) == {"canSendIn": 6, "sentLastHour": 1, "maxEmailsPerHour": 20}


def test_an_email_just_sent_counts_from_the_history_it_wrote(ks, home, smtp, keyring, tmp_path, capsys):
    """The count lives in the Send history, so a fresh run (e.g. after a shell restart) sees it."""
    write_shell_json(home, kindleAddress="reader@kindle.com", senderAddress="sender@gmail.com")
    keyring.set_password("abcd efgh ijkl mnop\n")
    book = tmp_path / "Dune.epub"
    book.write_bytes(b"PK tiny epub")
    ks.main(["send", "--route", "email", str(book)])
    capsys.readouterr()

    result = limit(ks, capsys)

    assert result["sentLastHour"] == 1
    assert 9 <= result["canSendIn"] <= 10
