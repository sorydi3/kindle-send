"""Program.js: the path of the kindle-send bundled in the plugin folder (spec §17). Run with node."""
import json

from qmljs import evaluate, needs_node

pytestmark = needs_node


def path(url):
    return evaluate("Program.js", f"path({json.dumps(url)})")


def test_the_bundled_program_is_run_by_its_file_path():
    url = "file:///home/u/.config/omarchy/plugins/sorydi3.kindle-send/bin/kindle-send"

    assert path(url) == "/home/u/.config/omarchy/plugins/sorydi3.kindle-send/bin/kindle-send"


def test_a_plugin_folder_with_spaces_or_accents_gives_the_real_path():
    url = "file:///home/u/My%20Code/k%C3%A9/bin/kindle-send"

    assert path(url) == "/home/u/My Code/ké/bin/kindle-send"
