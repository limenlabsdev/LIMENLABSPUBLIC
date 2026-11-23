# LIMEN Labs Public

Open-source research and tools for computational design and architectural software.

## Tools

| Tool | What it does | Version |
|---|---|---|
| [`inspect3dm`](inspect3dm/) | Checks `.3dm` files against a rule profile (validity, units, tolerances, meshes, layers, Revit import limits) | v0.2.0 |
| [`3dm-diff`](3dm-diff/) | Compares two `.3dm` files by object and layer ID; Markdown/JSON report; `git diff` driver | v0.1.0 |
| [`ghx-deps`](ghx-deps/) | Lists the plug-ins, components and file paths a Grasshopper `.ghx` needs; allowlist CI gate | v0.1.0 |

All three are alpha, run headless without Rhino, are tested on synthetic files on Linux, and install from a checkout (no PyPI or Food4Rhino listing).

## inspect3dm

[`inspect3dm`](inspect3dm/) is a headless, rule-based inspector for Rhino `.3dm` files. It reads a model or a folder, checks it against a rule profile, and writes a Markdown or JSON report. The Rhino application is not required.

This is **v0.2 / alpha**, not a finished product. New in v0.2: a `revit` profile that flags edges and curves shorter than Revit's short-curve tolerance (about 0.79 mm), geometry beyond Revit's 10-mile and 20-mile distance limits, missing units, and coarse tolerances, before the file goes to Revit. It reads the `.3dm` only and has been tested on synthetic files, not against Revit itself. See [CHANGELOG](inspect3dm/CHANGELOG.md).

- Tested on Linux only. Windows and macOS should install via `rhino3dm` wheels but are untested.
- Large (5–10 GB) files are untested.
- Validity results come from McNeel's openNURBS library (via rhino3dm) and may differ from Rhino's Check command.
- The tool reports problems; it does not repair models, and it is not a substitute for Check.

### Try it

```text
git clone https://github.com/ferall0gic/LIMENLABSPUBLIC.git
cd LIMENLABSPUBLIC
python -m pip install ./inspect3dm
3dm-inspect inspect3dm/samples/sample.3dm
3dm-inspect your-model.3dm --profile revit
```

See the [inspect3dm README](inspect3dm/README.md) for options, exit codes, profiles, and known limits.

### Run the tests

```text
python -m pip install -e "./inspect3dm[test]"
python -m pytest inspect3dm/tests
```

## 3dm-diff

[`3dm-diff`](3dm-diff/) shows what changed between two revisions of a `.3dm` file: objects added, removed or changed (geometry, layer, name, user text), layer changes, and document settings. It can also make `git diff` readable for `.3dm` files. Tested on synthetic files only and not across Rhino versions; see its [README](3dm-diff/README.md).

```text
python -m pip install ./3dm-diff
3dm-diff old.3dm new.3dm
```

## ghx-deps

[`ghx-deps`](ghx-deps/) lists what Grasshopper `.ghx` definitions need: recorded plug-in libraries, components, script components, clusters, and absolute file paths. With an allowlist it can fail a CI build. It reads **`.ghx` only; binary `.gh` is not supported**. See its [README](ghx-deps/README.md).

```text
python -m pip install ./ghx-deps
ghx-deps definitions/ --allowlist office-plugins.txt
ghx-deps-diff previous.ghx current.ghx
```

## License

MIT. See [LICENSE](LICENSE). Copyright (c) 2026 Sydney DeVille.

## Feedback

This is an early release. Please [open an issue](https://github.com/ferall0gic/LIMENLABSPUBLIC/issues) if you try any of the tools — especially if you can test on Windows or macOS, compare results with Rhino's Check command, or compare `--profile revit` findings with what Revit reports on import.
