"""Install generated functions into the open editor and check the result. Needs the editor running with the MCP
server (unreal-vscode, http://127.0.0.1:8100/mcp) and the WWModTools plugin.

    python -m fdgen.install <Name> ...      emit, define signatures, import bodies, compile + save, verify links
    python -m fdgen.install --dry <Name>    only emit (to .build/install/)
    python -m fdgen.install --manifest      refresh tests/blueprint_vars.json from the Blueprints' member variables

Install order: every function's signature is defined first (so bodies that call each other resolve), then the
bodies. Functions are grouped by target Blueprint (registry.target). After compiling, each graph is exported again
and its links are compared with the generated T3D: a link that was generated but is missing in the editor is an
error; extra links in the editor are expected only on the function entry / result nodes.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

from fdgen.__main__ import emit
from fdgen.registry import BLUEPRINTS, GRAPHS, SPECS, target

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".build" / "install"
MANIFEST = ROOT / "tests" / "blueprint_vars.json"
URL = "http://127.0.0.1:8100/mcp"
WW = "WWModTools.WWBlueprintToolset"


class Mcp:
    """Just enough of an MCP client for the editor's streamable-HTTP server."""

    def __init__(self, url=URL):
        self.url, self.session, self.ids = url, None, 0
        self._post({"jsonrpc": "2.0", "id": self._id(), "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "fdgen", "version": "1"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _id(self):
        self.ids += 1
        return self.ids

    def _post(self, body):
        headers = {"Content-Type": "application/json", "Accept": "application/json,text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(self.url, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=600) as r:
            self.session = r.headers.get("Mcp-Session-Id", self.session)
            text = r.read().decode("utf-8")
        if not text.strip():
            return None
        if text.lstrip().startswith("{"):
            return json.loads(text)
        data = [l[5:].strip() for l in text.splitlines() if l.startswith("data:")]   # server-sent events
        return json.loads(data[-1]) if data else None

    def tool(self, tool_name, **arguments):
        """Call a WWBlueprintToolset tool; returns its returnValue string."""
        res = self._post({"jsonrpc": "2.0", "id": self._id(), "method": "tools/call",
                          "params": {"name": "call_tool",
                                     "arguments": {"toolset_name": WW, "tool_name": tool_name, "arguments": arguments}}})
        if "error" in res:
            raise RuntimeError(f"{tool_name}: {res['error']}")
        result = res["result"]
        text = "".join(c.get("text", "") for c in result.get("content", []))
        if result.get("isError"):
            raise RuntimeError(f"{tool_name}: {text}")
        try:
            return json.loads(text).get("returnValue", text)
        except ValueError:
            return text


def _links(text):
    """{(node, pin, node, pin)} for every link, by node label (fdgen names each node by its label)."""
    nodes = {}
    for m in re.finditer(r'^Begin Object Class=\S+ Name="([^"]+)"[^\n]*\n(.*?)^End Object', text, re.M | re.S):
        nodes[m.group(1)] = m.group(2)
    pin_name = {}
    raw = []
    for node, body in nodes.items():
        for pm in re.finditer(r"CustomProperties Pin \((.*)\)\s*$", body, re.M):
            s = pm.group(1)
            pid = re.search(r"PinId=(\w+)", s).group(1)
            pname = re.search(r'PinName="([^"]*)"', s).group(1)
            pin_name[(node, pid)] = pname
            lt = re.search(r"LinkedTo=\(([^()]*)\)", s)
            for t in (lt.group(1).split(",") if lt else []):
                if t.strip():
                    tn, tp = t.split()
                    raw.append((node, pname, tn, tp))
    return {(a, ap, b, pin_name.get((b, bp), bp)) for a, ap, b, bp in raw}


def verify(generated, exported):
    """Links the generator made that the editor doesn't have, and links the editor added outside entry/result."""
    gen, got = _links(generated), _links(exported)
    entry_like = re.compile(r"^K2Node_Function(Entry|Result)_\d+$")
    missing = sorted(gen - got)
    extra = sorted(l for l in got - gen if not (entry_like.match(l[0]) or entry_like.match(l[2])))
    return missing, extra


def install(names, save=True):
    unknown = [n for n in names if n not in SPECS]
    if unknown:
        raise SystemExit(f"no install spec for: {', '.join(unknown)}")
    mcp = Mcp()
    ok = True
    for bp in BLUEPRINTS:
        group = [n for n in names if target(n) == bp]
        if not group:
            continue
        out = BUILD / bp
        for old in out.glob("*"):
            old.unlink()
        emit(str(out), group)
        specs = [out / f"{i:02d}_{n}.json" for i, n in enumerate(group, 1)]
        path = BLUEPRINTS[bp]
        for sig_only in (True, False):
            for name, spec in zip(group, specs):
                r = mcp.tool("ImportFunction", blueprintPath=path, specFile=str(spec), signatureOnly=sig_only)
                if not sig_only:
                    print(f"{bp}.{name}: {r.strip()}")
        print(f"{bp} compile: {mcp.tool('CompileAndSave', blueprintPath=path, save=save).strip()}")
        for name in group:
            after = out / f"after_{name}.t3d"
            mcp.tool("ExportGraph", blueprintPath=path, graphName=name, outFile=str(after))
            missing, extra = verify(GRAPHS[name](), after.read_text(encoding="utf-8", errors="replace"))
            status = "links ok" if not missing and not extra else ""
            print(f"  verify {name}: {status}")
            for l in missing:
                ok = False
                print(f"    MISSING {l[0]}.{l[1]} -> {l[2]}.{l[3]}")
            for l in extra:
                ok = False
                print(f"    EXTRA   {l[0]}.{l[1]} -> {l[2]}.{l[3]}")
    return ok


def refresh_manifest():
    mcp = Mcp()
    manifest = {"_comment": "Member variables of the target Blueprints (name -> pin type), from "
                            "WWBlueprintToolset.ListGraphs. Refresh with: uv run python -m fdgen.install --manifest"}
    for bp, path in BLUEPRINTS.items():
        listing = mcp.tool("ListGraphs", blueprintPath=path)
        manifest[bp] = {m.group(1): m.group(2) for m in
                        re.finditer(r"^variable (\S+) (\(.*\)) =", listing, re.M)}
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{MANIFEST}: " + ", ".join(f"{bp} {len(v)} variables" for bp, v in manifest.items() if bp != "_comment"))


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    if argv[0] == "--manifest":
        refresh_manifest()
    elif argv[0] == "--dry":
        for bp in BLUEPRINTS:
            group = [n for n in argv[1:] if target(n) == bp]
            if group:
                emit(str(BUILD / bp), group)
    else:
        sys.exit(0 if install(argv) else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
