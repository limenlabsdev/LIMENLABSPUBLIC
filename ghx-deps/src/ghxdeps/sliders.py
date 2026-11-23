"""Report the saved values and ranges of top-level Grasshopper number sliders."""

import argparse
import json
import sys

from .manifest import GhxError, read_definition

SLIDER_TYPE = "57da07bd-ecab-415d-9d86-af36d7073abc"


def read_sliders(path):
    _, definition = read_definition(path)
    sliders = []
    for obj in definition.findall("chunks/chunk[@name='DefinitionObjects']/chunks/chunk[@name='Object']"):
        type_id = obj.findtext("items/item[@name='GUID']", "").strip().lower()
        if type_id != SLIDER_TYPE:
            continue
        container = obj.find("chunks/chunk[@name='Container']")
        if container is None:
            raise GhxError(f"'{path}' has a number slider without a Container chunk.")
        values = {item.get("name"): item.text for item in container.findall(
            "chunks/chunk[@name='Slider']/items/item"
        )}
        sliders.append({
            "id": container.findtext("items/item[@name='InstanceGuid']", ""),
            "nickname": container.findtext("items/item[@name='NickName']", ""),
            "value": values.get("Value"),
            "min": values.get("Min"),
            "max": values.get("Max"),
        })
    return sliders


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("definition")
    parser.add_argument("--json", action="store_true", help="emit an array of sliders")
    args = parser.parse_args(argv)
    try:
        sliders = read_sliders(args.definition)
    except (GhxError, OSError) as exc:
        print(f"ghx-sliders: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(sliders, indent=2))
    elif not sliders:
        print("No number sliders on the top-level canvas.")
    else:
        for slider in sliders:
            name = slider["nickname"] or "Number Slider"
            value, low, high = (slider[key] or "?" for key in ("value", "min", "max"))
            print(f"{name} [{slider['id']}] = {value} (range {low} to {high})")
    return 0
