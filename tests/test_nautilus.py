"""The Nautilus extension (spec §4), loaded with fake `gi` modules.

Nothing real is summoned or notified: the fake Gio.Subprocess records argv.
`kindle-send` on PATH is a link to the repo script, so the formats come from it.
"""
import sys
import types
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXTENSION = REPO / "nautilus" / "kindle-send.py"


class FakeMenuItem:
    def __init__(self, name, label, icon=None, **_):
        self.name, self.label, self.icon = name, label, icon
        self.handlers = []

    def connect(self, signal, handler, *data):
        self.handlers.append((signal, handler, data))

    def activate(self):
        for signal, handler, data in self.handlers:
            if signal == "activate":
                handler(self, *data)


class FakeSubprocess:
    started = []

    @classmethod
    def new(cls, argv, flags):
        cls.started.append(list(argv))
        return cls()


class FakeLocation:
    def __init__(self, path):
        self.path = path

    def get_path(self):
        return self.path


class FakeFile:
    """A Nautilus.FileInfo stand-in. path=None means a non-local file (sftp://)."""

    def __init__(self, path, directory=False):
        self.path, self.directory = path, directory

    def is_directory(self):
        return self.directory

    def get_location(self):
        return FakeLocation(self.path)


def fake_gi():
    gi = types.ModuleType("gi")
    gi.require_version = lambda name, version: None
    repository = types.ModuleType("gi.repository")
    repository.GObject = types.SimpleNamespace(GObject=type("GObject", (), {}))
    repository.Nautilus = types.SimpleNamespace(MenuProvider=type("MenuProvider", (), {}),
                                                MenuItem=FakeMenuItem)
    repository.Gio = types.SimpleNamespace(Subprocess=FakeSubprocess,
                                           SubprocessFlags=types.SimpleNamespace(NONE=0))
    gi.repository = repository
    return {"gi": gi, "gi.repository": repository}


@pytest.fixture
def ext(home, tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "kindle-send").symlink_to(REPO / "bin" / "kindle-send")
    monkeypatch.setenv("PATH", f"{bindir}:/usr/bin")
    for name, module in fake_gi().items():
        monkeypatch.setitem(sys.modules, name, module)
    FakeSubprocess.started = []
    loader = SourceFileLoader("kindle_send_nautilus", str(EXTENSION))
    module = module_from_spec(spec_from_loader("kindle_send_nautilus", loader))
    loader.exec_module(module)
    return module


def items(ext, *files):
    return ext.SendToKindle().get_file_items(list(files))


def test_one_supported_book_gets_a_send_to_kindle_item(ext, tmp_path):
    [item] = items(ext, FakeFile(str(tmp_path / "Dune.epub")))

    assert item.label == "Send to Kindle"


@pytest.mark.parametrize("files", [
    [FakeFile("/books/comic.cbz")],
    [FakeFile("/books/Books.epub", directory=True)],
    [FakeFile(None)],
    [],
])
def test_no_item_without_a_supported_local_file(ext, files):
    assert items(ext, *files) == []


def test_nautilus_3_style_window_argument_still_works(ext):
    [item] = ext.SendToKindle().get_file_items(object(), [FakeFile("/books/a.PDF")])

    assert item.label == "Send to Kindle"


def test_no_item_when_kindle_send_is_not_installed(ext, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))

    assert items(ext, FakeFile("/books/Dune.epub")) == []


def test_activating_summons_the_picker_with_only_the_supported_files(ext):
    [item] = items(ext,
                   FakeFile("/books/My Book é.epub"),
                   FakeFile("/books/Folder", directory=True),
                   FakeFile("/books/Notes.mobi"))

    item.activate()

    assert FakeSubprocess.started == [[
        "omarchy-shell", "shell", "summon", "sorydi3.kindle-send",
        '{"files": ["/books/My Book \\u00e9.epub", "/books/Notes.mobi"]}',
    ]]


def test_a_file_selected_twice_is_summoned_once(ext):
    [item] = items(ext, FakeFile("/books/a.epub"), FakeFile("/books/a.epub"))

    item.activate()

    assert FakeSubprocess.started[0][-1] == '{"files": ["/books/a.epub"]}'


def test_unsupported_files_in_a_mixed_selection_are_listed_in_a_notification(ext):
    [item] = items(ext,
                   FakeFile("/books/Dune.epub"),
                   FakeFile("/books/comic.cbz"),
                   FakeFile("/books/old book.djvu"))

    item.activate()

    notify, summon = FakeSubprocess.started
    assert notify == [
        "omarchy-notification-send", "--app-name", "Books to Kindle", "-g", "", "-u", "normal",
        "Left out 2 files", "comic.cbz, old book.djvu: Kindle can't take these formats.",
    ]
    assert summon[-1] == '{"files": ["/books/Dune.epub"]}'


def test_one_left_out_file_is_named_in_the_singular(ext):
    [item] = items(ext, FakeFile("/books/Dune.epub"), FakeFile("/books/comic.cbz"))

    item.activate()

    assert FakeSubprocess.started[0][-2:] == ["Left out 1 file",
                                             "comic.cbz: Kindle can't take this format."]
