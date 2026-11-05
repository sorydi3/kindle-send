import json


def run(ks, capsys, *argv):
    code = ks.main(list(argv))
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    return code, lines


def test_kindle_reports_absent_when_no_drive_is_mounted(ks, usb, capsys):
    assert run(ks, capsys, "kindle") == (0, [{"present": False}])


def test_kindle_finds_the_mount_of_a_drive_with_amazon_vendor_id(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "stick", vendor="0781", disk="sdb")
    mount = usb.plug(tmp_path / "media" / "Kindle", vendor="1949", disk="sdc")

    code, [line] = run(ks, capsys, "kindle")

    assert code == 0
    assert line["present"] is True
    assert line["mount"] == str(mount)
    assert isinstance(line["free"], int) and line["free"] > 0


def test_usb_send_copies_the_book_into_documents(ks, usb, tmp_path, capsys):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()
    book = tmp_path / "Big Atlas.pdf"
    book.write_bytes(b"%PDF-1.7 " + b"x" * 5000)

    code, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert code == 0
    assert lines == [{"stage": "copying"}, {"result": "copied"}]
    assert (kindle / "documents" / "Big Atlas.pdf").read_bytes() == book.read_bytes()
    assert sorted(p.name for p in (kindle / "documents").iterdir()) == ["Big Atlas.pdf"]
    [entry] = ks.read_history()
    assert (entry["name"], entry["route"], entry["result"]) == ("Big Atlas.pdf", "usb", "copied")


def make_book(tmp_path, name, content=b"book"):
    book = tmp_path / name
    book.write_bytes(content)
    return book


def test_usb_send_replaces_a_same_name_file_on_the_kindle(ks, usb, tmp_path, capsys):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()
    (kindle / "documents" / "Dune.mobi").write_bytes(b"old edition")
    book = make_book(tmp_path, "Dune.mobi", b"new edition")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines[-1] == {"result": "copied"}
    assert (kindle / "documents" / "Dune.mobi").read_bytes() == b"new edition"


def test_usb_send_creates_documents_if_missing(ks, usb, tmp_path, capsys):
    kindle = usb.plug(tmp_path / "Kindle", disk="sdc", partition="sdc1")
    book = make_book(tmp_path, "notes.txt")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines[-1] == {"result": "copied"}
    assert (kindle / "documents" / "notes.txt").read_bytes() == b"book"


def test_usb_send_without_a_kindle_fails_before_copying(ks, usb, tmp_path, capsys):
    book = make_book(tmp_path, "Atlas.pdf")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"result": "failed", "reason": "Kindle not plugged in. Plug it in and send again."}]
    assert ks.read_history()[-1]["result"] == "failed"


def test_usb_send_refuses_formats_the_kindle_cant_read(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle")
    book = make_book(tmp_path, "Essay.docx")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"result": "failed", "reason": "DOCX can't be read over USB. Send it by email."}]


def test_usb_send_of_a_missing_file_fails_before_looking_for_the_kindle(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(tmp_path / "Gone.pdf"))

    assert lines == [{"result": "failed", "reason": "File not found: Gone.pdf."}]


def test_usb_send_fails_when_the_kindle_is_short_of_space(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    book = make_book(tmp_path, "Atlas.pdf", b"x" * 3_000_000)
    monkeypatch.setattr(ks, "free_space", lambda mount: 1_000_000)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"result": "failed", "reason": "Not enough space on the Kindle (needs 3 MB)."}]
    assert not (kindle / "documents" / "Atlas.pdf").exists()


def test_eject_unmounts_the_partition_then_powers_off_the_disk(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "stick", vendor="0781", disk="sdb", partition="sdb1")
    usb.plug(tmp_path / "Kindle", disk="sdc", partition="sdc1")

    assert run(ks, capsys, "eject") == (0, [{"ejected": True}])
    assert usb.calls() == ["unmount -b /dev/sdc1", "power-off -b /dev/sdc"]


def test_eject_of_a_whole_disk_kindle_uses_the_disk_for_both(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle", disk="sdc")

    assert run(ks, capsys, "eject") == (0, [{"ejected": True}])
    assert usb.calls() == ["unmount -b /dev/sdc", "power-off -b /dev/sdc"]


def test_eject_without_a_kindle_says_so(ks, usb, capsys):
    assert run(ks, capsys, "eject") == (0, [{"ejected": False, "reason": "Kindle not plugged in."}])
    assert usb.calls() == []


def test_eject_failure_gives_udisks_first_error_line(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle", disk="sdc")
    usb.fail_eject("Error unmounting /dev/sdc: GDBus.Error: target is busy\nmore detail")

    code, [line] = run(ks, capsys, "eject")

    assert code == 0
    assert line == {"ejected": False, "reason": "Error unmounting /dev/sdc: GDBus.Error: target is busy"}
    assert usb.calls() == ["unmount -b /dev/sdc"]
