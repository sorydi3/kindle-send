"""`kindle-send pick FILE...`: open the Picker with just these Books (spec §4), as Strata's action does."""
import json
import os
import stat

import pytest


@pytest.fixture
def shell(tmp_path, monkeypatch):
    """A fake `omarchy-shell` first on PATH that logs its argv as one JSON line."""
    directory = tmp_path / "shell-bin"
    directory.mkdir()
    log = tmp_path / "shell.log"
    fake = directory / "omarchy-shell"
    fake.write_text("#!/usr/bin/env python3\nimport json, sys\n"
                    f"open({str(log)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return log


def summons(log):
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def make(directory, *names):
    paths = []
    for name in names:
        path = directory / name
        path.write_bytes(b"x")
        paths.append(path)
    return paths


def test_pick_summons_the_picker_with_the_books(ks, shell, tmp_path):
    pdf, epub = make(tmp_path, "Dune.pdf", "Emma.epub")

    code = ks.main(["pick", str(pdf), str(epub)])

    assert code == 0
    assert summons(shell) == [["shell", "summon", "sorydi3.kindle-send",
                               json.dumps({"files": [str(pdf), str(epub)]})]]


def test_pick_leaves_out_unsupported_files_and_folders_and_names_them(ks, shell, tmp_path, capsys):
    pdf, cbz = make(tmp_path, "Dune.pdf", "Comic.cbz")
    folder = tmp_path / "Shelf.pdf"
    folder.mkdir()

    code = ks.main(["pick", str(pdf), str(cbz), str(folder)])

    assert code == 0
    assert json.loads(summons(shell)[0][3]) == {"files": [str(pdf)]}
    assert "Comic.cbz" in capsys.readouterr().err


def test_pick_with_no_supported_file_opens_nothing(ks, shell, tmp_path):
    (cbz,) = make(tmp_path, "Comic.cbz")

    assert ks.main(["pick", str(cbz)]) == 1
    assert summons(shell) == []


def test_pick_passes_names_with_spaces_and_accents_unchanged(ks, shell, tmp_path):
    (book,) = make(tmp_path, "Mon livre été 'v2'.PDF")

    ks.main(["pick", str(book)])

    assert json.loads(summons(shell)[0][3]) == {"files": [str(book)]}


def test_pick_makes_relative_paths_absolute(ks, shell, tmp_path, monkeypatch):
    make(tmp_path, "Dune.pdf")
    monkeypatch.chdir(tmp_path)

    ks.main(["pick", "Dune.pdf"])

    assert json.loads(summons(shell)[0][3]) == {"files": [str(tmp_path / "Dune.pdf")]}
