"""`kindle-send formats`: the one list of supported formats (spec §5), read by the Nautilus extension."""
import json


def test_formats_prints_every_format_either_route_takes(ks, capsys):
    code = ks.main(["formats"])

    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert code == 0
    assert lines == [{"formats": sorted([
        "epub", "pdf", "txt", "doc", "docx", "rtf", "html", "htm",
        "jpg", "jpeg", "png", "gif", "bmp", "azw3", "azw", "mobi", "prc", "kfx",
    ])}]
