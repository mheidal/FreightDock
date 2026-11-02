"""Engine and game references in generated graphs exist in the header dump (Automation/diff.hpp): called functions
on their class (or a base), and member variables read or written on another object. Catches typos and game
renames before an install turns them into "could not find function" compile errors."""
import re

import pytest

import headers
from fdgen.registry import GRAPHS
from t3d import parse

# Real functions the dump leaves out (it is incomplete for some engine libraries).
NOT_IN_DUMP = {("UKismetMathLibrary", n) for n in ("Abs", "Acos", "Cos", "Max", "Min", "Round", "Sin", "Sqrt")}

pytestmark = pytest.mark.skipif(not headers.DUMP.exists(), reason=f"no header dump at {headers.DUMP}")


@pytest.mark.parametrize("name", sorted(GRAPHS))
def test_references_exist(name):
    problems = []
    for n in parse(GRAPHS[name]()).values():
        for key, kind in (("FunctionReference", "functions"), ("VariableReference", "fields")):
            ref = n.props.get(key, "")
            parent = re.search(r'MemberParent="([^"]+)"', ref)
            member = re.search(r'MemberName="([^"]+)"', ref)
            if not parent or not member or "/Game/" in parent.group(1):
                continue   # self / local context, or one of the mod's own assets
            t = headers.lookup(parent.group(1))
            if t is None:
                problems.append(f"{n.name}: class {parent.group(1)} not in the dump")
                continue
            if (t.name, member.group(1)) in NOT_IN_DUMP:
                continue
            if not any(member.group(1) in getattr(x, kind) for x in headers.chain(t)):
                problems.append(f"{n.name}: {t.name} has no {kind[:-1]} {member.group(1)}")
    assert not problems, "\n".join(problems)
