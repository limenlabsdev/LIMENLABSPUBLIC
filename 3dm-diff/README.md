# 3dm-diff

> **v0.1.0, alpha.** Part of [LIMEN Labs Public](https://github.com/ferall0gic/LIMENLABSPUBLIC). Tested on synthetic files only; please report what you find in an issue.

`3dm-diff` compares two Rhino `.3dm` files without Rhino and tells you what changed between them: objects added, removed, or changed (geometry, layer, name, user text), layers added, removed, renamed, or restyled, and document settings and document user text. It prints Markdown for people or JSON for scripts, uses `diff`-style exit codes, and can act as a **git textconv driver**, so `git diff` on a `.3dm` shows readable line changes instead of "Binary files differ".

It reads the files with McNeel's `rhino3dm` (openNURBS) and never modifies them.

## Install (from a checkout)

```text
python -m pip install ./3dm-diff        # Python 3.10–3.14; installs rhino3dm>=8,<9
python -m pip install -e "./3dm-diff[test]" && python -m pytest 3dm-diff/tests
```

## Use

```text
3dm-diff tower_P01.3dm tower_P02.3dm
3dm-diff old.3dm new.3dm --format json --output changes.json
3dm-diff old.3dm new.3dm --match-geometry       # pair objects whose ID changed but geometry did not
3dm-diff old.3dm new.3dm --ignore user_text     # skip a field (name, user_text, layer)
```

Example output (from the synthetic fixtures in `scripts/make_fixtures.py`):

```text
Objects: 1 added, 1 removed, 2 changed, 1 unchanged. 2 layer changes; document settings changed; document text changed.

| Change | Object ID | Type | Layer | Detail |
|---|---|---|---|---|
| added | 20000000-…-000000000005 | Brep | A-WALL | C1 |
| removed | 20000000-…-000000000004 | LineCurve | A-WALL | Grid A |
| changed | 20000000-…-000000000002 | Brep | A-WALL | geometry (bounding-box centre moved 500 millimeters, same size) |
| changed | 20000000-…-000000000003 | Brep | A-DOOR-INT | layer: A-DOOR → A-DOOR-INT; user text fire_rating: 30 → 60 |
```

| Exit code | Meaning |
|---|---|
| 0 | No differences |
| 1 | Differences found |
| 2 | A file could not be read, or the command line was wrong |

### `git diff` for .3dm files

```text
echo "*.3dm diff=3dm" >> .gitattributes
git config diff.3dm.textconv "3dm-diff --textconv"
git diff model.3dm
```

`--textconv` prints one line per setting, layer, and object, sorted by layer, type, and ID, so a revision shows up as `-`/`+` lines. Each object line has a 12-character geometry hash.

## How it decides what changed

- **Matching:** objects and layers are matched by their IDs (GUIDs), which Rhino keeps when a file is saved. Copy/Paste, Import, or some scripts give objects new IDs. With `--match-geometry`, a removed object and an added object that have identical geometry, type, and layer are shown as one *re-identified* object.
- **Geometry:** two objects have the same geometry when the SHA-256 of their openNURBS serialization (from `rhino3dm`'s `Encode()`) is the same. That is exact, not a tolerance check. For changed geometry the report also gives how far the bounding-box centre moved and whether the box changed size. It does not measure how much the shape changed.
- **Attributes:** layer (full path), object name, and user text (key/value). Colors, materials, display order, and groups are not compared in v0.1.

## Limits (read before relying on it)

- Tested on synthetic files generated with `rhino3dm` 8.35.0 on Linux only. Not tested on files saved by different Rhino versions. Equal geometry may serialize differently across versions; that would appear as a geometry change with the same bounding box.
- Block definitions, annotations' text content, materials, views, and plug-in data are not compared.
- Object geometry that `rhino3dm` cannot read is shown as type `Unknown` with no hash.
- No GUI, no network, no telemetry.

## Report issues

Open an issue at https://github.com/ferall0gic/LIMENLABSPUBLIC/issues with the command you ran, the `--version` line, and the output. Attach a file only if you are allowed to share it.

## License

MIT (see LICENSE). `rhino3dm` is McNeel's, under the MIT license. No third-party code is included.

### Single-model reports

| Command | JSON output |
|---|---|
| `3dm-views model.3dm` | Saved named views in archive order, with projection type, camera location in model coordinates, and direction and up vectors as stored. Excludes ordinary working viewports. Returns an empty array for a model without named views. |
| `3dm-layers model.3dm` | One row per layer with its ID, full path, visibility, lock state and direct object count. Includes empty layers. Unresolved layer indices have their own row with null ID and path. Counts are from the saved object table, without expanding block placements. |
| `3dm-tags model.3dm` | Document user text plus object IDs, names and attribute user strings for tagged objects. Geometry-attached user data is outside its scope. |
| `3dm-duplicates model.3dm` | Groups of object IDs with the same SHA-256 digest of serialized geometry, regardless of layer or attribute name. Distinct serializations of visually identical shapes may differ. Objects the library cannot hash appear in a separate list. |

Installed with `python -m pip install ./3dm-diff` from the repository root. Redirect stdout to save a report. Successful reads exit 0, including empty results. Invalid input exits 2 with a diagnostic on stderr. These tools read the file without modifying it.
