"""Read the plug-in libraries, components and file references stored in a .ghx file.

A .ghx is the XML form of Grasshopper's GH_IO archive: nested ``<chunk>``
elements holding typed ``<item>`` values. This module reads it with the
standard-library XML parser and never imports GH_IO.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SCRIPT_COMPONENT_NAMES = frozenset({
    "C# Script", "VB Script", "Python 3 Script", "IronPython 2 Script",
    "GhPython Script", "Python Script",
})
FILE_EXTENSIONS = (
    ".3dm", ".gh", ".ghx", ".csv", ".txt", ".json", ".xml", ".xlsx", ".xls", ".dwg", ".dxf",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".shp", ".geojson", ".obj", ".stl",
    ".ifc", ".epw", ".gha", ".dll",
)
_ABS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/)")


class GhxError(Exception):
    """The file could not be read as a .ghx definition. Message is user-facing."""


@dataclass(frozen=True)
class Library:
    name: str
    version: str
    assembly_version: str
    assembly_full_name: str
    author: str
    id: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version, "assembly_version": self.assembly_version,
                "assembly_full_name": self.assembly_full_name, "author": self.author, "id": self.id}

    @property
    def display_version(self) -> str:
        return self.version or self.assembly_version or ""


@dataclass
class Manifest:
    path: str
    grasshopper_version: str | None = None
    archive_version: str | None = None
    libraries: list[Library] = field(default_factory=list)
    components: Counter = field(default_factory=Counter)   # (name, type guid) -> count
    script_components: Counter = field(default_factory=Counter)
    clusters: int = 0
    file_references: list[str] = field(default_factory=list)

    @property
    def object_count(self) -> int:
        return sum(self.components.values())


def _items(chunk) -> dict[str, ET.Element]:
    items = chunk.find("items") if chunk is not None else None
    if items is None:
        return {}
    return {i.get("name"): i for i in items.findall("item")}


def _text(chunk, name: str) -> str:
    el = _items(chunk).get(name)
    return (el.text or "").strip() if el is not None else ""


def _version(el) -> str | None:
    if el is None:
        return None
    parts = [(el.findtext(k) or "").strip() for k in ("Major", "Minor", "Revision")]
    return ".".join(parts) if any(parts) else (el.text or "").strip() or None


def _subchunks(chunk, name: str):
    chunks = chunk.find("chunks") if chunk is not None else None
    return [] if chunks is None else chunks.findall(f"chunk[@name='{name}']")


def _child(chunk, name: str):
    found = _subchunks(chunk, name)
    return found[0] if found else None


def read_definition(path: str | Path) -> tuple[ET.Element, ET.Element]:
    p = Path(path)
    if p.suffix.lower() == ".gh":
        raise GhxError(
            f"'{p}' is a binary .gh file. ghx-deps reads .ghx (XML) only: in Grasshopper use "
            "File > Save As and choose .ghx, then run again.")
    try:
        root = ET.parse(p).getroot()
    except FileNotFoundError:
        raise GhxError(f"'{p}' does not exist. Check the path.") from None
    except IsADirectoryError:
        raise GhxError(f"'{p}' is a folder.") from None
    except ET.ParseError as exc:
        raise GhxError(f"'{p}' is not valid XML ({exc}). It may be truncated or not a .ghx file.") from None
    if root.tag != "Archive":
        raise GhxError(f"'{p}' is XML but not a Grasshopper archive (root element <{root.tag}>).")
    definition = _child(root, "Definition")
    if definition is None:
        raise GhxError(f"'{p}' has no Definition chunk; it is not a Grasshopper definition.")

    return root, definition


def read_manifest(path: str | Path) -> Manifest:
    root, definition = read_definition(path)
    m = Manifest(path=str(path))
    m.archive_version = _version(_items(root).get("ArchiveVersion"))
    m.grasshopper_version = _version(_items(definition).get("plugin_version"))

    libs = _child(definition, "GHALibraries")
    for lib in _subchunks(libs, "Library"):
        m.libraries.append(Library(
            name=_text(lib, "Name"), version=_text(lib, "Version"),
            assembly_version=_text(lib, "AssemblyVersion"),
            assembly_full_name=_text(lib, "AssemblyFullName"),
            author=_text(lib, "Author"), id=_text(lib, "Id")))
    m.libraries.sort(key=lambda x: (x.name.lower(), x.id))

    objects = _child(definition, "DefinitionObjects")
    for obj in _subchunks(objects, "Object"):
        name, guid = _text(obj, "Name"), _text(obj, "GUID")
        m.components[(name, guid)] += 1
        if name in SCRIPT_COMPONENT_NAMES:
            m.script_components[name] += 1
        if name == "Cluster":
            m.clusters += 1

    refs = set()
    for item in definition.iter("item"):
        if item.get("type_name") != "gh_string":
            continue
        value = (item.text or "").strip()
        if value and "\n" not in value and _ABS_PATH.match(value) and value.lower().endswith(FILE_EXTENSIONS):
            refs.add(value)
    m.file_references = sorted(refs)
    return m


def discover(paths) -> tuple[list[Path], list[Path]]:
    """(ghx files, gh files) under the given files/folders, sorted."""
    ghx, gh = [], []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() == ".ghx":
                    ghx.append(f)
                elif f.is_file() and f.suffix.lower() == ".gh":
                    gh.append(f)
        elif p.suffix.lower() == ".gh":
            gh.append(p)
        else:
            ghx.append(p)
    return ghx, gh
