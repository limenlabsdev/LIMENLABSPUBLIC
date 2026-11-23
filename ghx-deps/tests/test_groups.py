import json
import xml.etree.ElementTree as ET

from ghxdeps.groups import GROUP_TYPE, main
from make_fixtures import BOX, ghx


def test_group_members(tmp_path, capsys):
    group = ("Group", GROUP_TYPE)
    root = ET.fromstring(ghx([], [group, group, BOX]))
    containers = root.findall(".//chunk[@name='Object']/chunks/chunk[@name='Container']/items")
    ids = [items.findtext("item[@name='InstanceGuid']") for items in containers]
    ET.SubElement(containers[0], "item", name="NickName").text = "Frame"
    for ref in (ids[2], ids[1], "missing"):
        ET.SubElement(containers[0], "item", name="ID").text = ref
    path = tmp_path / "groups.ghx"
    ET.ElementTree(root).write(path)
    assert main([str(path), "--json"]) == 0
    parent, nested = json.loads(capsys.readouterr().out)
    assert parent["id"] == ids[0]
    assert parent["nickname"] == "Frame"
    box, child, unresolved = parent["members"]
    assert box == {"id": ids[2], "object": {"name": "Box", "nickname": ""}}
    assert child["id"] == nested["id"] == ids[1]
    assert child["object"]["name"] == "Group" and nested["members"] == []
    assert unresolved == {"id": "missing", "object": None}
    assert main([str(path)]) == 0
    assert "(unresolved member) [missing]" in capsys.readouterr().out


def test_no_groups_and_invalid_input(fx, capsys):
    assert main([str(fx["core_only.ghx"]), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main([str(fx["binary.gh"]), "--json"]) == 2
    output = capsys.readouterr()
    assert output.out == "" and "binary" in output.err
