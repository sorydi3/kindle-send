"""Shared fixtures.

bin/kindle-send is one standard-library script with no .py extension. Tests load
it as a module (``ks`` fixture) and call ``ks.main(argv)`` in-process, so system
boundaries (smtplib.SMTP_SSL, tools on PATH) can be faked.
"""
import json
import os
import stat
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "kindle-send"


def load_script():
    loader = SourceFileLoader("kindle_send", str(SCRIPT))
    module = module_from_spec(spec_from_loader("kindle_send", loader))
    loader.exec_module(module)
    return module


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A temp HOME with XDG dirs, so nothing real is read or written."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.delenv("KINDLE_SEND_SHELL_JSON", raising=False)
    return home


@pytest.fixture
def ks(home):
    return load_script()


def write_shell_json(home, **settings):
    path = home / ".config" / "omarchy" / "shell.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"id": "sorydi3.kindle-send", **settings}
    path.write_text(json.dumps({"plugins": [{"id": "other.plugin"}, entry]}))
    return path


class FakeKeyring:
    """A fake `secret-tool` first on PATH. Logs its argv, prints the stored password.

    `secret-tool store` stands in for the user typing at its own prompt: it
    stores whatever `will_type()` set (nothing, if it wasn't called).
    """

    def __init__(self, tmp_path, monkeypatch):
        self.dir = tmp_path / "fakebin"
        self.dir.mkdir()
        self.store = tmp_path / "keyring-password"
        self.typed = tmp_path / "keyring-typed"
        self.log = tmp_path / "secret-tool.log"
        tool = self.dir / "secret-tool"
        tool.write_text(
            "#!/bin/bash\n"
            f'echo "$@" >> "{self.log}"\n'
            'if [ "$1" = store ]; then\n'
            f'  [ -f "{self.typed}" ] && cp "{self.typed}" "{self.store}"\n'
            "  exit 0\n"
            "fi\n"
            f'[ -f "{self.store}" ] || exit 1\n'
            f'cat "{self.store}"\n'
        )
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{self.dir}{os.pathsep}{os.environ['PATH']}")

    def set_password(self, password):
        self.store.write_text(password)

    def will_type(self, password):
        self.typed.write_text(password)

    def password(self):
        return self.store.read_text() if self.store.exists() else None

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def keyring(tmp_path, monkeypatch, home):
    return FakeKeyring(tmp_path, monkeypatch)


class FakeSMTP:
    """Stands in for smtplib.SMTP_SSL. Never touches the network."""

    instances = []
    advertised_size = 35882577
    login_error = None
    connect_error = None
    send_error = None

    def __init__(self, host, port, *args, **kwargs):
        if FakeSMTP.connect_error:
            raise FakeSMTP.connect_error
        self.host, self.port = host, port
        self.logins = []
        self.sent = []
        self.esmtp_features = {}
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self, *args):
        if FakeSMTP.advertised_size is not None:
            self.esmtp_features["size"] = str(FakeSMTP.advertised_size)
        return (250, b"ok")

    def login(self, user, password):
        if FakeSMTP.login_error:
            raise FakeSMTP.login_error
        self.logins.append((user, password))

    def send_message(self, msg, *args, **kwargs):
        if FakeSMTP.send_error:
            raise FakeSMTP.send_error
        self.sent.append(msg)
        return {}

    def quit(self):
        pass


@pytest.fixture
def smtp(ks, monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.advertised_size = 35882577
    FakeSMTP.login_error = None
    FakeSMTP.connect_error = None
    FakeSMTP.send_error = None
    monkeypatch.setattr(ks.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP
