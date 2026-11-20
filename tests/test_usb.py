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


def test_usb_send_without_a_kindle_fails_before_copying_and_leaves_no_history(ks, usb, tmp_path, capsys):
    book = make_book(tmp_path, "Atlas.pdf")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"result": "failed", "code": "kindle_not_plugged_in", "values": {},
        "reason": "Kindle not plugged in. Plug it in and send again."}]
    # The Service makes it a Pending Send; it is recorded once it is copied (or fails for another reason).
    assert ks.read_history() == []


def test_usb_send_refuses_formats_the_kindle_cant_read(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle")
    book = make_book(tmp_path, "Essay.docx")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"result": "failed", "code": "format_not_for_usb", "values": {"format": "DOCX"},
                      "reason": "DOCX can't be read over USB. Send it by email."}]


def test_usb_send_of_a_missing_file_fails_before_looking_for_the_kindle(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(tmp_path / "Gone.pdf"))

    assert lines == [{"result": "failed", "code": "file_not_found", "values": {"name": "Gone.pdf"},
                      "reason": "File not found: Gone.pdf."}]


def test_usb_send_fails_when_the_kindle_is_short_of_space(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    book = make_book(tmp_path, "Atlas.pdf", b"x" * 3_000_000)
    monkeypatch.setattr(ks, "free_space", lambda mount: 1_000_000)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == [{"result": "failed", "code": "kindle_full", "values": {"mb": 3},
                      "reason": "Not enough space on the Kindle (needs 3 MB)."}]
    assert not (kindle / "documents" / "Atlas.pdf").exists()


def test_a_copy_that_fails_part_way_names_the_error_and_leaves_nothing(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    book = make_book(tmp_path, "Atlas.pdf")

    def broken(src, dst, length=0):
        raise OSError(5, "Input/output error")
    monkeypatch.setattr(ks.shutil, "copyfileobj", broken)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines[-1] == {"result": "failed", "code": "copy_failed", "values": {"detail": "Input/output error"},
                         "reason": "Couldn't copy to the Kindle: Input/output error."}
    assert list((kindle / "documents").iterdir()) == []


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
    assert run(ks, capsys, "eject") == (0, [{"ejected": False, "code": "eject_no_kindle", "values": {},
                                                  "reason": "Kindle not plugged in."}])
    assert usb.calls() == []


def test_eject_failure_gives_udisks_first_error_line(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle", disk="sdc")
    usb.fail_eject("Error unmounting /dev/sdc: GDBus.Error: target is busy\nmore detail")

    code, [line] = run(ks, capsys, "eject")

    assert code == 0
    assert line == {"ejected": False, "code": "eject_failed",
                    "values": {"detail": "Error unmounting /dev/sdc: GDBus.Error: target is busy"},
                    "reason": "Error unmounting /dev/sdc: GDBus.Error: target is busy"}
    assert usb.calls() == ["unmount -b /dev/sdc"]


def test_an_eject_step_that_fails_silently_is_named(ks, usb, tmp_path, capsys):
    usb.plug(tmp_path / "Kindle", disk="sdc")
    usb.fail_eject("")

    _, [line] = run(ks, capsys, "eject")

    assert line == {"ejected": False, "code": "eject_step_failed", "values": {"step": "unmount"},
                    "reason": "unmount failed."}


# --- The Kindle must still be there when the copy starts (spec §7) ------------------------

def gone_during_conversion(ks, monkeypatch, tmp_path, swap):
    """An EPUB whose Conversion runs `swap()` (the Kindle going away) before it finishes."""
    def convert(book, workdir):
        swap()
        target = workdir / f"{book.stem}.azw3"
        target.write_bytes(b"AZW3")
        return target
    monkeypatch.setattr(ks, "convert_for_usb", convert)
    return make_book(tmp_path, "Dune.epub")


NOT_PLUGGED_IN = [
    {"result": "failed", "code": "kindle_not_plugged_in", "values": {},
     "reason": "Kindle not plugged in. Plug it in and send again."}]


def test_a_kindle_unmounted_during_conversion_gets_nothing_written_to_its_empty_folder(
        ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()

    def unplug():
        (kindle / "documents").rmdir()  # what the mount held is gone; the folder stays
        usb.unmount(kindle)
    book = gone_during_conversion(ks, monkeypatch, tmp_path, unplug)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == NOT_PLUGGED_IN
    assert list(kindle.iterdir()) == []
    assert ks.read_history() == []


def test_a_mount_folder_that_is_no_longer_a_mount_point_gets_nothing(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    book = gone_during_conversion(ks, monkeypatch, tmp_path, lambda: usb.forget_mount(kindle))

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == NOT_PLUGGED_IN
    assert list(kindle.iterdir()) == []


def test_a_different_folder_now_at_the_kindles_mount_gets_nothing(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()

    def swap():  # another file system now sits at the same path
        kindle.rename(tmp_path / "old-kindle")
        kindle.mkdir()
    book = gone_during_conversion(ks, monkeypatch, tmp_path, swap)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines == NOT_PLUGGED_IN
    assert list(kindle.iterdir()) == []
    assert list((tmp_path / "old-kindle" / "documents").iterdir()) == []


# --- Two copies of the same Book at once (spec §7) ---------------------------------------

def test_two_sends_of_the_same_book_at_once_both_copy_and_leave_no_staging_file(
        ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()
    book = make_book(tmp_path, "Atlas.pdf", b"%PDF-1.7 atlas")
    real_copy = ks.shutil.copyfileobj
    interleaved = []

    def copy_then_let_the_other_send_run(src, dst, length=0):
        real_copy(src, dst, length)
        if not interleaved:  # the Picker's send runs while the CLI's is mid-copy
            interleaved.append(True)
            ks.main(["send", "--route", "usb", str(book)])
    monkeypatch.setattr(ks.shutil, "copyfileobj", copy_then_let_the_other_send_run)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert [l for l in lines if "result" in l] == [{"result": "copied"}, {"result": "copied"}]
    assert sorted(p.name for p in (kindle / "documents").iterdir()) == ["Atlas.pdf"]
    assert (kindle / "documents" / "Atlas.pdf").read_bytes() == b"%PDF-1.7 atlas"


def test_a_send_leaves_another_sends_staging_file_alone(ks, usb, tmp_path, capsys):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()
    others = [kindle / "documents" / ".Atlas.pdf.part", kindle / "documents" / ".Atlas.pdf.k3x9q1.part"]
    for other in others:
        other.write_bytes(b"another send, still copying")
    book = make_book(tmp_path, "Atlas.pdf", b"%PDF-1.7 atlas")

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines[-1] == {"result": "copied"}
    assert all(o.read_bytes() == b"another send, still copying" for o in others)
    assert sorted(p.name for p in (kindle / "documents").iterdir()) == sorted(
        ["Atlas.pdf"] + [o.name for o in others])


def test_a_failed_copy_removes_only_its_own_staging_file(ks, usb, tmp_path, capsys, monkeypatch):
    kindle = usb.plug(tmp_path / "Kindle")
    (kindle / "documents").mkdir()
    other = kindle / "documents" / ".Atlas.pdf.k3x9q1.part"
    other.write_bytes(b"another send, still copying")
    book = make_book(tmp_path, "Atlas.pdf")

    def broken(src, dst, length=0):
        raise OSError(5, "Input/output error")
    monkeypatch.setattr(ks.shutil, "copyfileobj", broken)

    _, lines = run(ks, capsys, "send", "--route", "usb", str(book))

    assert lines[-1]["code"] == "copy_failed"
    assert sorted(p.name for p in (kindle / "documents").iterdir()) == [other.name]
