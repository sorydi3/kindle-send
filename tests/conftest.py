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


@pytest.fixture(autouse=True)
def no_real_keyring(tmp_path, monkeypatch):
    """Every test gets an empty fake `secret-tool` first on PATH, so the real
    keyring is never read, even by a test that forgot the `keyring` fixture.
    The `keyring` fixture puts its own fake in front of this one."""
    guard = tmp_path / "guardbin"
    guard.mkdir()
    tool = guard / "secret-tool"
    tool.write_text("#!/bin/sh\nexit 1\n")
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{guard}{os.pathsep}{os.environ['PATH']}")


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


class FakeUsb:
    """Fake `lsblk`, `udevadm` and `udisksctl` first on PATH, so no test sees a real drive.

    `plug()` adds a mounted drive backed by a temp dir. `udisksctl` only logs its
    argv; `fail_eject()` makes it exit 1 with an error on stderr.
    """

    def __init__(self, tmp_path, monkeypatch):
        self.dir = tmp_path / "fakeusb"
        self.dir.mkdir()
        self.devices = []
        self.lsblk_json = tmp_path / "lsblk.json"
        self.vendor_dir = tmp_path / "vendors"
        self.vendor_dir.mkdir()
        self.log = tmp_path / "udisksctl.log"
        self.eject_error = tmp_path / "udisksctl.error"
        self._write()
        self._tool("lsblk", f'cat "{self.lsblk_json}"\n')
        self._tool(
            "udevadm",
            'for a in "$@"; do case "$a" in --name=*) dev="${a#--name=}";; esac; done\n'
            f'f="{self.vendor_dir}/$(basename "$dev")"\n'
            '[ -f "$f" ] || exit 1\n'
            'echo "DEVNAME=$dev"\n'
            'echo "ID_BUS=usb"\n'
            'echo "ID_VENDOR_ID=$(cat "$f")"\n',
        )
        self._tool(
            "udisksctl",
            f'echo "$@" >> "{self.log}"\n'
            f'if [ -f "{self.eject_error}" ]; then cat "{self.eject_error}" >&2; exit 1; fi\n',
        )
        monkeypatch.setenv("PATH", f"{self.dir}{os.pathsep}{os.environ['PATH']}")

    def _tool(self, name, body):
        tool = self.dir / name
        tool.write_text("#!/bin/bash\n" + body)
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)

    def _write(self):
        self.lsblk_json.write_text(json.dumps({"blockdevices": self.devices}))

    def plug(self, mount, vendor="1949", disk="sdx", partition=None):
        """A drive mounted at `mount`: the whole disk, or `partition` of it."""
        mount.mkdir(parents=True, exist_ok=True)
        self.devices.append({"name": disk, "path": f"/dev/{disk}", "pkname": None, "type": "disk",
                             "mountpoints": [] if partition else [str(mount)]})
        if partition:
            self.devices.append({"name": partition, "path": f"/dev/{partition}", "pkname": disk,
                                 "type": "part", "mountpoints": [str(mount)]})
        for name in (disk, partition):
            if name:
                (self.vendor_dir / name).write_text(vendor)
        self._write()
        return mount

    def fail_eject(self, message):
        self.eject_error.write_text(message + "\n")

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def usb(tmp_path, monkeypatch, home):
    return FakeUsb(tmp_path, monkeypatch)
