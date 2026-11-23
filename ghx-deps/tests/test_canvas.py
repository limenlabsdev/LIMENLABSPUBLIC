from xml.etree import ElementTree as ET

from ghxdeps.canvas import notes, wires


def definition(*objects):
    return ET.fromstring('<chunk><chunks><chunk name="DefinitionObjects"><chunks>'
                         + ''.join(objects) + '</chunks></chunk></chunks></chunk>')


def chunk(name, **items):
    element = ET.Element("chunk", name=name)
    fields = ET.SubElement(element, "items")
    for key, value in items.items():
        ET.SubElement(fields, "item", name=key).text = value
    return element


def with_children(parent, *children):
    ET.SubElement(parent, "chunks").extend(children)
    return parent


def object_xml(name, guid, container):
    return ET.tostring(with_children(chunk("Object", Name=name, GUID=guid), container), encoding="unicode")


def test_panel_and_scribble_keep_multiline_and_empty_text():
    panel = object_xml("Panel", "59e0b89a-e487-49f8-bab8-b5bab16be14c",
                       chunk("Container", InstanceGuid="a", UserText=" A\nB "))
    scribble = object_xml("Scribble", "7f5c6c55-f846-4a08-9c9a-cfdc285cc6fe",
                          chunk("Container", InstanceGuid="b", Text=""))
    assert [(r["kind"], r["text"]) for r in notes(definition(panel, scribble))] == [
        ("Panel", " A\nB "), ("Scribble", "")]


def test_wires_resolve_forward_reference_and_keep_unknown_source():
    legacy = chunk("param_input", Name="Radius", InstanceGuid="input", Source="OUT")
    modern = with_children(chunk("ParameterData"), chunk("OutputParam", Name="R", InstanceGuid="out"))
    target = object_xml("Consumer", "", with_children(chunk("Container", InstanceGuid="a"), legacy))
    source = object_xml("Producer", "", with_children(chunk("Container", InstanceGuid="b"), modern))
    dangling = object_xml("Panel", "", chunk("Container", InstanceGuid="c", Source="missing"))
    first, second = wires(definition(target, source, dangling))
    assert first == {"source_id": "out", "target_id": "input",
                     "source": {"object_id": "b", "object_name": "Producer", "port_name": "R"},
                     "target": {"object_id": "a", "object_name": "Consumer", "port_name": "Radius"}}
    assert second["source"] is None and second["source_id"] == "missing"
