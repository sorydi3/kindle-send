"""EPUB Conversion for the USB Route (spec §8), with a fake `ebook-convert` on PATH."""
import json
import os
import stat

import pytest


def run(ks, capsys, *argv):
    code = ks.main(list(argv))
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    return code, lines


class FakeCalibre:
    """A fake `ebook-convert` first on PATH. It logs its argv and writes `AZW3:<input bytes>`."""

    def __init__(self, tmp_path, monkeypatch):
        self.dir = tmp_path / "fakecalibre"
        self.dir.mkdir()
        self.log = tmp_path / "ebook-convert.log"
        self.error = tmp_path / "ebook-convert.error"
        tool = self.dir / "ebook-convert"
        tool.write_text(
            "#!/bin/bash\n"
            f'printf "%s\\n" "$@" >> "{self.log}"\n'
            'echo "Converting input to HTML..."\n'
            f'if [ -f "{self.error}" ]; then cat "{self.error}" >&2; exit 1; fi\n'
            '{ printf "AZW3:"; cat "$1"; } > "$2"\n'
        )
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{self.dir}{os.pathsep}{os.environ['PATH']}")

    def fail(self, stderr):
        self.error.write_text(stderr)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def calibre(tmp_path, monkeypatch):
    return FakeCalibre(tmp_path, monkeypatch)


def test_epub_is_converted_to_azw3_and_copied(ks, usb, calibre, tmp_path, capsys):
    kindle = usb.plug(tmp_path / "Kindle")
    book = tmp_path / "Dune.epub"
    book.write_bytes(b"epub bytes")

    code, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert code == 0
    assert lines == [{"stage": "converting"}, {"stage": "copying"}, {"result": "copied"}]
    assert sorted(p.name for p in (kindle / "documents").iterdir()) == ["Dune.azw3"]
    assert (kindle / "documents" / "Dune.azw3").read_bytes() == b"AZW3:epub bytes"


def test_conversion_leaves_the_epub_alone_and_deletes_the_azw3(ks, usb, calibre, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle")
    book = tmp_path / "Dune.epub"
    book.write_bytes(b"epub bytes")
    before = book.stat().st_mtime_ns

    run(ks, capsys, "send", "--route", "usb", str(book))

    source, target = calibre.calls()
    assert source == str(book)
    assert target.endswith("/Dune.azw3") and not target.startswith(str(tmp_path / "Kindle"))
    assert not os.path.exists(os.path.dirname(target))
    assert book.read_bytes() == b"epub bytes" and book.stat().st_mtime_ns == before
    assert [p.name for p in tmp_path.iterdir() if p.suffix == ".azw3"] == []


def test_without_calibre_the_epub_fails_with_how_to_install(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    book = tmp_path / "Dune.epub"
    book.write_bytes(b"epub bytes")
    monkeypatch.setattr(ks, "EBOOK_CONVERT", "ebook-convert-not-installed-here")

    code, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert code == 0
    assert lines == [{"stage": "converting"},
                     {"result": "failed",
                      "reason": "Install calibre to send EPUB over USB (sudo pacman -S calibre)."}]
    assert not (kindle / "documents").exists() or list((kindle / "documents").iterdir()) == []
    [entry] = ks.read_history()
    assert (entry["route"], entry["result"]) == ("usb", "failed")


def test_failed_conversion_reports_the_first_error_line_and_copies_nothing(ks, usb, calibre, tmp_path, capsys):
    kindle = usb.plug(tmp_path / "Kindle")
    book = tmp_path / "Dune.epub"
    book.write_bytes(b"epub bytes")
    calibre.fail("\nDRMError: This book is locked by DRM.\nTraceback (most recent call last):\n  File x\n")

    code, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert code == 0
    assert lines == [{"stage": "converting"},
                     {"result": "failed", "reason": "Couldn't convert: DRMError: This book is locked by DRM."}]
    assert not (kindle / "documents").exists() or list((kindle / "documents").iterdir()) == []
    assert book.read_bytes() == b"epub bytes"


def test_non_epub_books_skip_conversion(ks, usb, calibre, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle")
    book = tmp_path / "Atlas.pdf"
    book.write_bytes(b"%PDF")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"stage": "copying"}, {"result": "copied"}]
    assert calibre.calls() == []
