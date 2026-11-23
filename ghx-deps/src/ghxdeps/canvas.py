"""Read notes and wires from the saved top-level Grasshopper canvas."""

import argparse
import json
import sys

from .manifest import GhxError, read_definition

NOTE_TYPES = {
    "59e0b89a-e487-49f8-bab8-b5bab16be14c": ("Panel", "UserText"),
    "7f5c6c55-f846-4a08-9c9a-cfdc285cc6fe": ("Scribble", "Text"),
}


def item(chunk, name):
    return chunk.findtext(f"items/item[@name='{name}']", "")


def canvas(definition):
    for obj in definition.findall("chunks/chunk[@name='DefinitionObjects']/chunks/chunk[@name='Object']"):
        container = obj.find("chunks/chunk[@name='Container']")
        if container is not None:
            yield obj, container


def notes(definition):
    rows = []
    for obj, container in canvas(definition):
        kind = NOTE_TYPES.get(item(obj, "GUID").lower())
        if kind:
            label, field = kind
            rows.append({"kind": label, "id": item(container, "InstanceGuid"),
                         "nickname": item(container, "NickName"), "text": item(container, field)})
    return rows


def ports(container, direction):
    modern = container.findall(f"chunks/chunk[@name='ParameterData']/chunks/chunk[@name='{direction.title()}Param']")
    legacy = container.findall(f"chunks/chunk[@name='param_{direction}']")
    return [container, *modern, *legacy]


def wires(definition):
    outputs = {}
    links = []
    for obj, container in canvas(definition):
        owner = {"object_id": item(container, "InstanceGuid"), "object_name": item(obj, "Name")}
        for port in ports(container, "output"):
            port_id = item(port, "InstanceGuid").lower()
            if port_id:
                outputs[port_id] = {**owner, "port_name": item(port, "Name")}
        for port in ports(container, "input"):
            for source in port.findall("items/item[@name='Source']"):
                links.append({"source_id": (source.text or "").lower(),
                              "target_id": item(port, "InstanceGuid").lower(),
                              "target": {**owner, "port_name": item(port, "Name")}})
    for link in links:
        link["source"] = outputs.get(link["source_id"])
    return links


def run(report, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("definition")
    args = parser.parse_args()
    try:
        _, definition = read_definition(args.definition)
        print(json.dumps(report(definition), indent=2))
    except (GhxError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def notes_cli():
    return run(notes, "Export saved Panel text and Scribble annotations as JSON.")


def wires_cli():
    return run(wires, "Trace saved wire endpoints and their owning objects as JSON.")
