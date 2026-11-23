"""Read a .3dm into a plain, comparable snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import rhino3dm


class ReadError(Exception):
    """A file could not be read. The message is user-facing."""


def _unit_name(unit_system) -> str:
    raw = getattr(unit_system, "name", str(unit_system).split(".")[-1])
    return re.sub(r"(?<!^)(?=[A-Z])", " ", raw).lower()


def geometry_hash(geom) -> str | None:
    """SHA-256 of the openNURBS serialization of a geometry object.

    Only the serialized bytes are hashed (not the archive or library version
    stamps), so the same geometry read by the same rhino3dm version always gives
    the same hash. A different Rhino version may serialize equal geometry
    differently; that shows up as a geometry change with an unchanged bounding box.
    """
    if geom is None:
        return None
    try:
        enc = geom.Encode()
    except Exception:
        return None
    data = enc.get("data") if isinstance(enc, dict) else None
    payload = data if isinstance(data, str) else json.dumps(enc, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bbox(geom) -> tuple[float, float, float, float, float, float] | None:
    if geom is None:
        return None
    try:
        bb = geom.GetBoundingBox()  # no-arg form; GetBoundingBox(True) raises in rhino3dm 8 (#721)
    except Exception:
        return None
    if bb is None or not bb.IsValid:
        return None
    return (bb.Min.X, bb.Min.Y, bb.Min.Z, bb.Max.X, bb.Max.Y, bb.Max.Z)


def _user_strings(obj) -> dict[str, str]:
    try:
        pairs = obj.GetUserStrings()
    except Exception:
        return {}
    return {str(k): str(v) for k, v in pairs}


@dataclass(frozen=True)
class LayerRec:
    id: str
    name: str
    full_path: str
    color: tuple[int, int, int, int]
    visible: bool
    locked: bool

    def fields(self) -> dict[str, Any]:
        return {"full_path": self.full_path, "color": list(self.color),
                "visible": self.visible, "locked": self.locked}


@dataclass(frozen=True)
class ObjectRec:
    id: str
    type: str
    layer: str | None
    name: str
    user_text: tuple[tuple[str, str], ...]
    geometry_hash: str | None
    bbox: tuple[float, ...] | None

    def fields(self) -> dict[str, Any]:
        return {"type": self.type, "layer": self.layer, "name": self.name,
                "user_text": dict(self.user_text), "geometry": self.geometry_hash}


@dataclass
class Snapshot:
    path: str
    settings: dict[str, Any]
    document_text: dict[str, str]
    layers: dict[str, LayerRec] = field(default_factory=dict)
    objects: dict[str, ObjectRec] = field(default_factory=dict)


def read_model(path: str) -> rhino3dm.File3dm:
    p = Path(path)
    if not p.exists():
        raise ReadError(f"'{path}' does not exist. Check the path.")
    if p.is_dir():
        raise ReadError(f"'{path}' is a folder. Pass a .3dm file.")
    if p.stat().st_size == 0:
        raise ReadError(f"'{path}' is empty (0 bytes).")
    model = rhino3dm.File3dm.Read(str(p))
    if model is None:
        raise ReadError(f"'{path}' is not a readable .3dm file (or is truncated).")

    return model


def load_snapshot(path: str) -> Snapshot:
    model = read_model(path)
    s = model.Settings
    settings = {
        "units": _unit_name(s.ModelUnitSystem),
        "absolute_tolerance": float(s.ModelAbsoluteTolerance),
        "angle_tolerance_degrees": round(float(s.ModelAngleToleranceDegrees), 9),
    }
    doc_text: dict[str, str] = {}
    try:
        strings = model.Strings
        for i in range(len(strings)):
            k, v = strings[i]
            doc_text[str(k)] = str(v)
    except Exception:
        pass

    snap = Snapshot(path=str(path), settings=settings, document_text=doc_text)
    index_to_path: dict[int, str] = {}
    for i in range(len(model.Layers)):
        layer = model.Layers[i]
        full = layer.FullPath or layer.Name or ""
        index_to_path[i] = full
        c = tuple(int(x) for x in layer.Color)
        snap.layers[str(layer.Id)] = LayerRec(str(layer.Id), layer.Name or "", full, c,
                                              bool(layer.Visible), bool(layer.Locked))
    for obj in model.Objects:
        geom = obj.Geometry
        attrs = obj.Attributes
        oid = str(attrs.Id)
        snap.objects[oid] = ObjectRec(
            id=oid,
            type=type(geom).__name__ if geom is not None else "Unknown",
            layer=index_to_path.get(attrs.LayerIndex),
            name=attrs.Name or "",
            user_text=tuple(sorted(_user_strings(attrs).items())),
            geometry_hash=geometry_hash(geom),
            bbox=_bbox(geom),
        )
    return snap
