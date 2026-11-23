"""Single-model JSON reports for Rhino handoffs."""

import argparse
from collections import Counter, defaultdict
import json
import sys

from .snapshot import ReadError, geometry_hash, read_model


def layers(model):
    counts = Counter(obj.Attributes.LayerIndex for obj in model.Objects)
    rows = []
    for layer in model.Layers:
        rows.append({"id": str(layer.Id), "index": layer.Index, "path": layer.FullPath or layer.Name,
                     "objects": counts.pop(layer.Index, 0), "visible": layer.Visible, "locked": layer.Locked})
    for index, count in sorted(counts.items()):
        rows.append({"id": None, "index": index, "path": None, "objects": count,
                     "visible": None, "locked": None})
    return rows


def tags(model):
    document = dict(model.Strings[i] for i in range(len(model.Strings)))
    objects = []
    for obj in model.Objects:
        attrs = obj.Attributes
        values = dict(attrs.GetUserStrings() or ())
        if values:
            objects.append({"id": str(attrs.Id), "name": attrs.Name or "", "values": values})
    return {"document": document, "objects": objects}


def duplicates(model):
    buckets = defaultdict(list)
    unreadable = []
    for obj in model.Objects:
        oid = str(obj.Attributes.Id)
        digest = geometry_hash(obj.Geometry)
        if digest is None:
            unreadable.append(oid)
        else:
            buckets[digest].append(oid)
    return {"groups": [{"sha256": digest, "object_ids": sorted(ids)}
                       for digest, ids in sorted(buckets.items()) if len(ids) > 1],
            "unhashed_object_ids": sorted(unreadable)}


def run(report, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("model")
    args = parser.parse_args()
    try:
        print(json.dumps(report(read_model(args.model)), indent=2))
    except (ReadError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def layers_cli():
    return run(layers, "Count object-table entries on each Rhino layer, including empty layers.")


def tags_cli():
    return run(tags, "Export document user text and object attribute user strings.")


def duplicates_cli():
    return run(duplicates, "Find object IDs with identical serialized geometry.")


def named_views(model):
    """Return saved named cameras in model order, including repeated names."""
    rows = []
    for view in model.NamedViews:
        vp = view.Viewport
        if vp.IsTwoPointPerspectiveProjection:
            projection = "two-point perspective"
        elif vp.IsPerspectiveProjection:
            projection = "perspective"
        elif vp.IsParallelProjection:
            projection = "parallel"
        else:
            projection = "unknown"
        rows.append({
            "name": view.Name,
            "projection": projection,
            "camera_location": [vp.CameraLocation.X, vp.CameraLocation.Y, vp.CameraLocation.Z],
            "camera_direction": [vp.CameraDirection.X, vp.CameraDirection.Y, vp.CameraDirection.Z],
            "camera_up": [vp.CameraUp.X, vp.CameraUp.Y, vp.CameraUp.Z],
        })
    return rows


def views_cli():
    return run(named_views, "Export saved Rhino named views and their camera frames as JSON.")
