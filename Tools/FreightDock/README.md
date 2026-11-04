# FreightDock Blueprint generator (`fdgen`)

FreightDock's logic lives in two Blueprints:
- **BP_MapLoad:** almost everything.
- **BP_Startup:** registering the building, the Mod Options and the Stevedore modifier.

Their function graphs are generated in Python as Unreal Blueprint clipboard text (T3D). They are installed into the open editor through the `unreal-vscode` MCP server and the WWModTools plugin (`WWBlueprintToolset`).

## Setup

Requires [uv](https://docs.astral.sh/uv/). From `Tools/FreightDock`:

```
uv sync
```

This creates `.venv` with pytest. The generator itself uses only the standard library.

## Commands

| Command | What it does |
|---|---|
| `uv run python -m fdgen --list` | Every function, its module, and whether it has an install spec |
| `uv run python -m fdgen <Name>` | T3D for one function on stdout |
| `uv run python -m fdgen --emit <dir> <Name> ...` | `NN_<Name>.t3d` + `NN_<Name>.json` (ImportFunction spec) per function |
| `uv run python -m fdgen.install <Name> ...` | Emit, install, compile + save, and verify links; needs the editor |
| `uv run python -m fdgen.install --dry <Name> ...` | Only emit, to `.build/install/<Blueprint>/` |
| `uv run python -m fdgen.install --manifest` | Refresh `tests/blueprint_vars.json` from the Blueprints; needs the editor |
| `uv run pytest` | All tests |
| `uv run pytest --update-golden` | Accept the current output as the new snapshot |
| `uv run python loom_test.py` | Test the Loom libraries' pure functions with Loom's test commandlet (headless editor, about 15 s) |

### What `fdgen.install` does

1. Groups the functions by target Blueprint (`registry.target`).
2. Defines every signature first (`ImportFunction`, `signatureOnly`), so that bodies calling each other resolve.
3. Imports the bodies, then runs `CompileAndSave`.
4. Exports each graph again and compares its links with the generated T3D.
   - A generated link missing in the editor is reported as `MISSING`.
   - Any extra link outside the function entry and result nodes is reported as `EXTRA`.
   - It exits non-zero on either.

Member variables are not created by `fdgen.install`. Add them with `WWBlueprintToolset.EnsureVariables` (it adds or updates). Delete them with `BlueprintTools.remove_variable`. Afterwards, refresh the manifest.

## Layout

```
fdgen/
  core/       generic: graph.py (Graph, render), types.py (pin types), paths.py (class / library / asset paths),
              nodes.py (node builders), text.py (format, log, toast), specs.py (fn_spec)
  features/   docks, pairing, options, startup, stevedore, freight, standins, voyages, deliver, arcs, debug
  routes/     cells, pathfind (A*), course (turns, spline), display (route lines), rescan
  registry.py GRAPHS / SPECS from every module; which Blueprint each function goes into
  __main__.py command line
  install.py  MCP client, install + verify, manifest refresh
tests/
  golden/     snapshot of every graph (GUIDs renumbered) and specs.json
  test_golden.py, test_lint.py, test_api.py, blueprint_vars.json, t3d.py (T3D reader), headers.py (header-dump reader)
```

Each module's docstring says what it covers.

A feature module defines builder functions and two tables:
- `GRAPHS = {"FunctionName": builder}`, where `builder()` returns the T3D text;
- optionally `SPECS = {"FunctionName": fn_spec(...)}`.

Only functions with a spec can be installed. The spec-less ones (CellKey, DockIdOf, …) date from when graphs were pasted by hand. Their Return node is wired by hand.

### Adding a function

1. Write `def my_function():` in the module it belongs to. Build a `Graph()` and give every node a unique, readable name: it becomes the node's label. End with `return g.render()`.
2. Add it to the module's `GRAPHS`, and to `SPECS` with `fn_spec(entry, inputs, outputs, locals_, returns, values, pure)`.
   - `entry` is the (node, pin) the function entry's `then` connects to.
   - `returns` are exec pins that lead to the Return node.
   - `values` are `(node, pin, output)` wirings to the Return node.
3. If it goes into BP_Startup, add its name to `registry.STARTUP_GRAPHS`.
4. Run `uv run pytest`. A new function has no snapshot yet, so run `uv run pytest --update-golden` once you're happy with it. Review what changed in `tests/golden` before accepting.
5. Run `uv run python -m fdgen.install MyFunction` with the editor open.

## Tests

Everything runs on the generated text; no editor is needed.

- **test_golden:** output is unchanged from the snapshot. Refactors must keep it identical. An intended change shows up as a diff to review, after which you run `--update-golden`.
- **test_lint:** structural checks on every graph:
  - links resolve, are symmetric, and join an output to an input;
  - an exec output has at most one link, and so does a data input;
  - linked pin types match (category and container; struct type);
  - map pins carry their value type, and a real value carries float or double;
  - every spec'd graph has no unused pure nodes, and every exec node is reachable from the entry;
  - spec entry, return and return-value pins exist;
  - no local shares a name with an input or output;
  - local variable nodes are declared in the spec;
  - every member variable used exists in the target Blueprint with the same type (`blueprint_vars.json`).
- **test_api:** functions called and fields accessed on engine or game classes exist in the header dump `Automation/diff.hpp`, including base classes. A few real engine functions that the dump omits are allowlisted. The test is skipped if the dump is missing.

The tests don't cover behaviour: whether a graph does the right thing in game. That still takes a Cook & Install and a play test.

## Conventions

- Every generated log line goes through `Stamp` (pure, output `Result`: `"[yyyy-mm-dd hh:mm:ss] [FreightDock] "`). Lines that use ModAPI's own date instead (BP_Startup, hand-built functions) start their message with `text.LOG_PREFIX`. Integers in log text are printed without thousands separators.
- Hand-built in the editor, not generated: the Event Graph, Toast, StockpileToString, CollectionToString, LogDocks, and the widget WBP_FDToast.
- Written in Loom, not here: the Freight Dock panel (`Content/Mods/FreightDock/UI/WBP_FDPanel.lm`, `WBP_FDLinkRow.lm`, `WBP_FDWantRow.lm`, `WBP_FDTip.lm`) the loading plan (`Loom/BPL_FDLoad.lm`, called by `UpdateRequest`), the unloading animation (`Loom/BP_FDFling.lm`), network storage (`Loom/BPL_FDNet.lm`: `PartnerOf`, `Unpair`) and the pairing key and arcs (`Loom/BPL_FDPairing.lm`: `PairAtCursor`, `DrawArcs`). Those four BP_MapLoad functions are one-call wrappers made with `nodes.loom_call`. When a generated function needs changing, its logic moves to Loom the same way. Generated graphs call Loom by path (`paths.FD_PANEL_CLASS`, `NET_LIB`, `PAIRING_LIB`), and they call BP_MapLoad's functions by name, so renaming a BP_MapLoad function or its pins also needs the `.lm` files changed.
