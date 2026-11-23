import json
import xml.etree.ElementTree as ET

from ghxdeps.sliders import SLIDER_TYPE, main
from make_fixtures import BOX, ghx


def test_slider_records(tmp_path, capsys):
    root = ET.fromstring(ghx([], [("Number Slider", SLIDER_TYPE)] * 2 + [BOX]))
    containers = root.findall(".//chunk[@name='Object']/chunks/chunk[@name='Container']")
    for container in containers[:2]:
        ET.SubElement(container.find("items"), "item", name="NickName").text = "Width"
    settings = ET.SubElement(ET.SubElement(containers[0], "chunks"), "chunk", name="Slider")
    items = ET.SubElement(settings, "items")
    for key, value in [("Value", "0.10000000000000001"), ("Min", "-1"), ("Max", "2")]:
        ET.SubElement(items, "item", name=key).text = value
    path = tmp_path / "design.ghx"
    ET.ElementTree(root).write(path)
    assert main([str(path), "--json"]) == 0
    first, second = json.loads(capsys.readouterr().out)
    assert first["nickname"] == second["nickname"] == "Width"
    assert first["id"] != second["id"]
    assert (first["min"], first["value"], first["max"]) == ("-1", "0.10000000000000001", "2")
    assert second["value"] is None


def test_empty_and_binary(fx, capsys):
    assert main([str(fx["core_only.ghx"]), "--json"]) == 0
    # Synthetic Number Slider objects in this fixture use a placeholder type GUID.
    assert json.loads(capsys.readouterr().out) == []
    assert main([str(fx["binary.gh"])]) == 2
    assert "binary" in capsys.readouterr().err
