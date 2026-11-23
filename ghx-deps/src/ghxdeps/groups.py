"""List canvas groups and their direct members in a Grasshopper XML definition."""

import argparse
import json
import sys

from .manifest import GhxError, read_definition

# Grasshopper's built-in Group type, independent of its displayed name.
GROUP_TYPE = "c552a431-af5b-46a9-a8a4-0fcbc27ef596"


def read_groups(path):
    _, definition = read_definition(path)
    objects = definition.findall("chunks/chunk[@name='DefinitionObjects']/chunks/chunk[@name='Object']")
    by_id = {}
    groups = []
    for obj in objects:
        container = obj.find("chunks/chunk[@name='Container']/items")
        if container is None:
            continue
        instance_id = container.findtext("item[@name='InstanceGuid']", "").strip().lower()
        name = obj.findtext("items/item[@name='Name']", "")
        nickname = container.findtext("item[@name='NickName']", "")
        if instance_id:
            by_id[instance_id] = {"name": name, "nickname": nickname}
        type_id = obj.findtext("items/item[@name='GUID']", "").strip().lower()
        if type_id == GROUP_TYPE:
            refs = [(item.text or "").strip().lower() for item in container.findall("item[@name='ID']")]
            groups.append((instance_id, nickname, refs))

    return [
        {"id": group_id, "nickname": nickname,
         "members": [{"id": ref, "object": by_id.get(ref)} for ref in refs]}
        for group_id, nickname, refs in groups
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition")
    parser.add_argument("--json", action="store_true", help="emit an array of groups")
    args = parser.parse_args(argv)
    try:
        groups = read_groups(args.definition)
    except (GhxError, OSError) as exc:
        print(f"ghx-groups: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(groups, indent=2))
    elif not groups:
        print("No groups on the top-level canvas.")
    else:
        for group in groups:
            print(f"{group['nickname'] or '(unnamed group)'} [{group['id']}]")
            for member in group["members"]:
                obj = member["object"]
                if obj is None:
                    label = "(unresolved member)"
                else:
                    label = obj["name"]
                    if obj["nickname"] and obj["nickname"] != label:
                        label += f" ({obj['nickname']})"
                print(f"  {label} [{member['id']}]")
    return 0
