"""Reflected classes and structs from the header dump (Automation/diff.hpp): name -> base, fields, functions."""
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

DUMP = Path(__file__).resolve().parents[3] / "Automation" / "diff.hpp"

_TYPE = re.compile(r"^(class|struct) (\w+)(?: : public (\w+))? \{\n(.*?)^\};", re.M | re.S)
_FUNC = re.compile(r"^\s+(?:static )?[\w:<>,*& ]+?[ *&](\w+)\((?:[^()]|\([^()]*\))*\)(?: const)?;", re.M)
_FIELD = re.compile(r"^\s+[\w:<>,*& ]+?[ *&](\w+);", re.M)


@dataclass
class Type:
    name: str
    base: str | None
    fields: set = field(default_factory=set)
    functions: set = field(default_factory=set)


@cache
def types():
    text = DUMP.read_text(encoding="utf-8", errors="replace")
    out = {}
    for kind, name, base, body in _TYPE.findall(text):
        out[name] = Type(name, base or None, set(_FIELD.findall(body)), set(_FUNC.findall(body)))
    return out


def lookup(path):
    """'/Script/Module.Name' (or a Class'...' reference) -> Type, trying the U/A/F prefixes; None if not in the dump."""
    short = re.sub(r"^.*[.']", "", path.rstrip("'\""))
    for prefix in ("U", "A", "F", ""):
        t = types().get(prefix + short)
        if t:
            return t
    return None


def chain(t):
    """t and its bases that are in the dump."""
    while t:
        yield t
        t = types().get(t.base) if t.base else None
