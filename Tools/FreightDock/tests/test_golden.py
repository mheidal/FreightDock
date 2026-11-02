"""Generated output must match the checked-in snapshot in tests/golden/.

A deliberate change to a graph or spec shows up here; review the diff, then refresh the snapshot with
    uv run pytest --update-golden
"""
import json
from pathlib import Path

import pytest

from fdgen.registry import GRAPHS, SPECS
from normalize import normalize_t3d

GOLDEN = Path(__file__).parent / "golden"


@pytest.mark.parametrize("name", sorted(GRAPHS))
def test_graph_matches_golden(name, update_golden):
    path = GOLDEN / f"{name}.t3d"
    text = normalize_t3d(GRAPHS[name]())
    if update_golden:
        path.write_text(text, encoding="utf-8", newline="\n")
        return
    assert path.exists(), f"no snapshot for {name}: run with --update-golden"
    assert text == path.read_text(encoding="utf-8"), f"{name} output changed"


def test_no_stale_snapshots(update_golden):
    stale = sorted(p.stem for p in GOLDEN.glob("*.t3d") if p.stem not in GRAPHS)
    if update_golden:
        for name in stale:
            (GOLDEN / f"{name}.t3d").unlink()
        return
    assert not stale, f"snapshots for removed graphs: {stale}"


def test_specs_match_golden(update_golden):
    path = GOLDEN / "specs.json"
    if update_golden:
        path.write_text(json.dumps(SPECS, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
        return
    assert SPECS == json.loads(path.read_text(encoding="utf-8"))
