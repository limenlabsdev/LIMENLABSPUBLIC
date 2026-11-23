import json

import pytest

from ghxdeps.diff import main
from make_fixtures import BOX, MESHKIT, PANEL_WITH_PATH, SLIDER, ghx


def test_inventory_diff(tmp_path, capsys):
    before = tmp_path / "before.ghx"
    after = tmp_path / "after.ghx"
    upgraded = (*MESHKIT[:1], "3.0", *MESHKIT[2:])
    before.write_text(ghx([MESHKIT], [SLIDER, SLIDER, BOX]))
    after.write_text(ghx([upgraded], [BOX, SLIDER, PANEL_WITH_PATH]))
    args = [str(before), str(after)]
    assert main(args) == 0
    assert "Number Slider" in capsys.readouterr().out
    assert main([*args, "--json", "--check"]) == 1
    changes = json.loads(capsys.readouterr().out)
    assert len(changes) == 5
    assert [(c["name"], c["before"], c["after"]) for c in changes
            if c["kind"] == "component"] == [("Number Slider", 2, 1), ("Read File", 0, 1)]
    assert [(c["version"], c["before"], c["after"]) for c in changes
            if c["kind"] == "library"] == [("2.1.0", 1, 0), ("3.0", 0, 1)]
    assert next(c for c in changes if c["kind"] == "file")["path"] == PANEL_WITH_PATH[2][0][1]


def test_reordered_objects(tmp_path, capsys):
    paths = [tmp_path / name for name in ("a.ghx", "b.ghx")]
    for path, objects in zip(paths, ([BOX, SLIDER], [SLIDER, BOX])):
        path.write_text(ghx([], objects))
    assert main([*map(str, paths), "--check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.parametrize("bad", ["not_xml.ghx", "binary.gh", "missing.ghx"])
def test_invalid_input(fx, bad, capsys):
    good = fx["core_only.ghx"]
    assert main([str(good), str(good.with_name(bad)), "--json"]) == 2
    output = capsys.readouterr()
    assert bad in output.err
    assert output.out == ""
