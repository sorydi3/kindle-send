"""The safety nets in conftest.py: no test reaches a real mail server."""
import shutil
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

TESTS = Path(__file__).resolve().parent


def run_inner(pytester, body):
    shutil.copy(TESTS / "conftest.py", pytester.path / "conftest.py")
    pytester.makepyfile(test_inner="import smtplib\n\n" + body)
    return pytester.runpytest("-q", "-p", "no:cacheprovider")


@pytest.mark.parametrize("cls", ["SMTP_SSL", "SMTP"])
def test_smtp_outside_the_smtp_fixture_fails_the_test(pytester, cls):
    result = run_inner(pytester, f"def test_connects():\n    smtplib.{cls}('smtp.example.com', 465)\n")

    result.assert_outcomes(failed=1, errors=1)
    result.stdout.fnmatch_lines(["*real SMTP*"])


def test_a_swallowed_smtp_attempt_still_fails_the_test(pytester):
    """kindle-send catches network errors and reports them, so refusing alone
    could go unnoticed: the guard fails the test at teardown too."""
    result = run_inner(pytester, (
        "def test_sends_quietly():\n"
        "    try:\n"
        "        smtplib.SMTP_SSL('smtp.example.com', 465)\n"
        "    except Exception:\n"
        "        pass\n"))

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*real SMTP*"])


def test_the_smtp_fixture_replaces_the_guard(ks, smtp):
    assert ks.smtplib.SMTP_SSL is smtp
