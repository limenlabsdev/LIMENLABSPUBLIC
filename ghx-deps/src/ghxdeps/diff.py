"""Compare dependency inventories recorded in two Grasshopper definitions."""

import argparse
from collections import Counter
import json
import sys

from .manifest import GhxError, read_manifest


def inventory(manifest):
    records = Counter()
    for lib in manifest.libraries:
        key = ("library", lib.name, lib.id, lib.version, lib.assembly_version)
        records[key] += 1
    for (name, guid), count in manifest.components.items():
        records[("component", name, guid)] = count
    for path in manifest.file_references:
        records[("file", path)] = 1
    return records


FIELDS = {
    "library": ("name", "id", "version", "assembly_version"),
    "component": ("name", "id"),
    "file": ("path",),
}


def compare(before, after):
    old, new = inventory(before), inventory(after)
    changes = []
    for key in sorted(old.keys() | new.keys()):
        if old[key] != new[key]:
            kind, *values = key
            changes.append({"kind": kind, **dict(zip(FIELDS[kind], values)),
                            "before": old[key], "after": new[key]})
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--json", action="store_true", help="emit a JSON array of changes")
    parser.add_argument("--check", action="store_true", help="return 1 for dependency changes")
    args = parser.parse_args(argv)
    try:
        changes = compare(read_manifest(args.before), read_manifest(args.after))
    except (GhxError, OSError) as exc:
        print(f"ghx-deps-diff: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(changes, indent=2))
    elif changes:
        for change in changes:
            kind = change["kind"]
            fields = " ".join(f"{key}={json.dumps(change[key])}" for key in FIELDS[kind])
            print(f"{kind} {fields}: {change['before']} -> {change['after']}")
    else:
        print("No dependency changes.")
    return 1 if args.check and changes else 0
