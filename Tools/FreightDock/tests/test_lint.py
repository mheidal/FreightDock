"""Structural checks on every generated graph and install spec - the mistakes that otherwise only show up as a
compile error (or silent miswiring) after an install."""
import json
import re
from functools import cache
from pathlib import Path

import pytest

from fdgen.registry import GRAPHS, SPECS, target
from t3d import parse, pin_index

NAMES = sorted(GRAPHS)
SPEC_NAMES = sorted(SPECS)


@cache
def graph(name):
    nodes = parse(GRAPHS[name]())
    return nodes, pin_index(nodes)


def fail_if(problems):
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("name", NAMES)
def test_links_resolve_and_are_symmetric(name):
    nodes, pins = graph(name)
    problems = []
    for p in pins.values():
        for target in p.links:
            q = pins.get(target)
            if q is None:
                problems.append(f"{p} -> {target}: no such pin")
            elif (p.node, p.id) not in q.links:
                problems.append(f"{p} -> {q}: not linked back")
    fail_if(problems)


@pytest.mark.parametrize("name", NAMES)
def test_links_join_output_to_input(name):
    nodes, pins = graph(name)
    fail_if([f"{p} -> {pins[t]}" for p in pins.values() if p.output for t in p.links
             if t in pins and pins[t].output])


@pytest.mark.parametrize("name", NAMES)
def test_link_fan_out(name):
    """An exec output drives one input; a data input reads from one output."""
    nodes, pins = graph(name)
    fail_if([f"{p}: {len(p.links)} links" for p in pins.values()
             if len(p.links) > 1 and (p.exec == p.output)])


def _compatible(a, b):
    if "wildcard" in (a.category, b.category):
        return True
    if a.category != b.category:
        return False
    if a.container != b.container:
        return False
    if a.category == "struct" and a.subobj and b.subobj and a.subobj != b.subobj:
        return False
    return True   # object classes are not compared (upcasts are fine); float <-> double converts implicitly


@pytest.mark.parametrize("name", NAMES)
def test_linked_pin_types_match(name):
    nodes, pins = graph(name)
    fail_if([f"{p} ({p.category}{'/' + p.container if p.container else ''}) -> {pins[t]} "
             f"({pins[t].category}{'/' + pins[t].container if pins[t].container else ''})"
             for p in pins.values() if p.output for t in p.links if t in pins and not _compatible(p, pins[t])])


@pytest.mark.parametrize("name", NAMES)
def test_map_values_are_typed(name):
    """A Map pin needs its value type; a real value needs its float/double subcategory (the editor drops it)."""
    nodes, pins = graph(name)
    fail_if([str(p) for p in pins.values() if p.container == "Map" and
             (not p.value_type or ('TerminalCategory="real"' in p.value_type and "TerminalSubCategory" not in p.value_type))])


@pytest.mark.parametrize("name", SPEC_NAMES)
def test_pure_nodes_are_used(name):
    """A node without exec pins whose outputs feed nothing is dead weight (usually a forgotten link). Nodes the
    install spec wires to the Return node count as used. Graphs without a spec are skipped: they were pasted by hand
    and their return values are wired by hand, so they always have unlinked pure nodes."""
    nodes, pins = graph(name)
    returned = {v[0] for v in SPECS.get(name, {}).get("returnValues", [])}
    fail_if([n.name for n in nodes.values()
             if n.name not in returned and not any(p.exec for p in n.pins) and any(p.output for p in n.pins)
             and not any(p.links for p in n.pins if p.output)])


@pytest.mark.parametrize("name", SPEC_NAMES)
def test_spec_pins_exist(name):
    nodes, _ = graph(name)
    spec = SPECS[name]
    problems = []

    def need(node, pin, what):
        n = nodes.get(node)
        if n is None:
            problems.append(f"{what}: no node {node}")
        elif n.pin(pin) is None:
            problems.append(f"{what}: {node} has no pin {pin}")

    need(*spec["entry"], "entry")
    for node, pin in spec["returns"]:
        need(node, pin, "return")
    for node, pin, _out in spec["returnValues"]:
        need(node, pin, "return value")
    outputs = {o["name"] for o in spec["outputs"]}
    problems += [f"return value targets unknown output {o}" for *_, o in spec["returnValues"] if o not in outputs]
    fail_if(problems)


@pytest.mark.parametrize("name", SPEC_NAMES)
def test_spec_names_unique(name):
    """A local may not share its name with an input or output (ImportFunction fails on it)."""
    spec = SPECS[name]
    names = [v["name"] for part in ("inputs", "outputs", "locals") for v in spec[part]]
    fail_if([f"{n} declared twice" for n in sorted({n for n in names if names.count(n) > 1})])


@pytest.mark.parametrize("name", SPEC_NAMES)
def test_spec_entry_reaches_every_exec_node(name):
    """Every node with an exec input is reachable along exec links from the entry pin."""
    nodes, pins = graph(name)
    spec = SPECS[name]
    entry_node = spec["entry"][0]
    seen, todo = set(), [entry_node]
    while todo:
        n = nodes.get(todo.pop())
        if n is None or n.name in seen:
            continue
        seen.add(n.name)
        for p in n.pins:
            if p.exec and p.output:
                todo += [t[0] for t in p.links]
    fail_if([n.name for n in nodes.values()
             if n.name not in seen and any(p.exec and not p.output for p in n.pins)])


@pytest.mark.parametrize("name", SPEC_NAMES)
def test_local_variable_nodes_are_declared(name):
    """A Get/Set of a function-scoped variable must name an input, output or local of that function."""
    nodes, _ = graph(name)
    spec = SPECS[name]
    declared = {v["name"] for part in ("inputs", "outputs", "locals") for v in spec[part]}
    problems = []
    for n in nodes.values():
        ref = n.props.get("VariableReference", "")
        if f'MemberScope="{name}"' in ref:
            var = ref.split('MemberName="')[1].split('"')[0]
            if var not in declared:
                problems.append(f"{n.name}: {var} not declared")
    fail_if(problems)


def _manifest_type(text):
    get = lambda k: (re.search(rf'{k}="?([^",)]*)', text) or [None, ""])[1]
    container = get("ContainerType")
    return get("PinCategory"), get("PinSubCategoryObject").strip("'\""), "" if container == "None" else container


MANIFEST = json.loads((Path(__file__).parent / "blueprint_vars.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", NAMES)
def test_member_variables_match_blueprint(name):
    """Every self-context variable a graph reads or writes is a member of the Blueprint it is installed into, with
    the same pin type (tests/blueprint_vars.json; refresh with `python -m fdgen.install --manifest`). Catches graphs
    still using a deleted variable, or a variable whose type changed."""
    members = MANIFEST[target(name)]
    nodes, _ = graph(name)
    problems = []
    for n in nodes.values():
        ref = n.props.get("VariableReference", "")
        if "bSelfContext=True" not in ref:
            continue
        var = re.search(r'MemberName="([^"]+)"', ref).group(1)
        if var not in members:
            problems.append(f"{n.name}: {target(name)} has no variable {var}")
            continue
        pin = n.pin(var)
        if pin is None:
            continue
        want = _manifest_type(members[var])
        have = (pin.category, pin.subobj.strip("'\""), pin.container)
        if want != have:
            problems.append(f"{n.name}: {var} is {want} in the Blueprint, {have} here")
    fail_if(problems)
