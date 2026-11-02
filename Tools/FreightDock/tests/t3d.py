"""Minimal reader for the T3D that fdgen renders: nodes, their pins, pin types and links."""
import re
from dataclasses import dataclass, field

_OBJ = re.compile(r'^Begin Object Class=(\S+) Name="([^"]+)"\n(.*?)^End Object', re.M | re.S)
_PIN = re.compile(r"^\s*CustomProperties Pin \((.*)\)\s*$", re.M)
_REF = re.compile(r"(\w+)=\(([^()]*)\)")


@dataclass
class Pin:
    node: str
    id: str
    name: str
    output: bool
    category: str
    subobj: str = ""
    subcat: str = ""
    container: str = ""
    value_type: str = ""
    default: str | None = None
    links: list = field(default_factory=list)   # [(node, pin id)]

    @property
    def exec(self):
        return self.category == "exec"

    def __str__(self):
        return f"{self.node}.{self.name}"


@dataclass
class Node:
    name: str
    cls: str
    props: dict
    pins: list

    @property
    def kind(self):
        return self.cls.rsplit(".", 1)[-1]

    def pin(self, name, output=None):
        for p in self.pins:
            if p.name == name and (output is None or p.output == output):
                return p
        return None


def _field(s, key):
    m = re.search(rf'(?:^|,){re.escape(key)}=("(?:[^"\\]|\\.)*"|\([^()]*\)|[^,]*)', s)
    return m.group(1).strip('"') if m else None


def parse(text):
    nodes = {}
    for m in _OBJ.finditer(text):
        cls, name, body = m.groups()
        props = {k: v for k, v in _REF.findall(body)}
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("CustomProperties") and "=" in line and not line.startswith(tuple(props)):
                k, v = line.split("=", 1)
                props.setdefault(k, v)
        pins = []
        for pm in _PIN.finditer(body):
            s = pm.group(1)
            linked = re.search(r"LinkedTo=\(([^()]*)\)", s)
            links = [tuple(x.split()) for x in linked.group(1).split(",") if x.strip()] if linked else []
            pins.append(Pin(node=name, id=_field(s, "PinId"), name=_field(s, "PinName"),
                            output=_field(s, "Direction") == "EGPD_Output",
                            category=_field(s, "PinType.PinCategory") or "",
                            subobj=_field(s, "PinType.PinSubCategoryObject") or "",
                            subcat=_field(s, "PinType.PinSubCategory") or "",
                            container=_field(s, "PinType.ContainerType") or "",
                            value_type=_field(s, "PinType.PinValueType") or "",
                            default=_field(s, "DefaultValue") or _field(s, "DefaultObject"),
                            links=links))
        assert name not in nodes, f"duplicate node name {name}"
        nodes[name] = Node(name, cls, props, pins)
    return nodes


def pin_index(nodes):
    """(node, pin id) -> Pin"""
    return {(n.name, p.id): p for n in nodes.values() for p in n.pins}
