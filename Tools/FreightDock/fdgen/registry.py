"""Every installable graph and its ImportFunction spec, collected from the feature modules.

A module contributes `GRAPHS` ({FunctionName: builder}, builder() -> T3D text) and optionally `SPECS`
({FunctionName: fn_spec(...)}). Only functions with a spec can be installed by `--emit`.
"""
from fdgen.features import (arcs, debug, deliver, docks, freight, options, pairing, standins, startup,
                            stevedore, voyages)
from fdgen.routes import cells, course, display, pathfind, rescan

MODULES = [docks, pairing, options, startup, stevedore, freight, standins, voyages, deliver, arcs, debug,
           cells, pathfind, course, display, rescan]

GRAPHS = {}
SPECS = {}
OWNER = {}   # FunctionName -> module name
for _m in MODULES:
    for _name, _builder in getattr(_m, "GRAPHS", {}).items():
        assert _name not in GRAPHS, f"{_name} defined in both {OWNER[_name]} and {_m.__name__}"
        GRAPHS[_name] = _builder
        OWNER[_name] = _m.__name__
    for _name, _spec in getattr(_m, "SPECS", {}).items():
        assert _name in getattr(_m, "GRAPHS", {}), f"{_m.__name__}: spec {_name} has no graph in the same module"
        SPECS[_name] = _spec

# Which Blueprint each function lives in. Everything not listed goes into BP_MapLoad.
BLUEPRINTS = {"BP_MapLoad": "/Game/Mods/FreightDock/BP_MapLoad", "BP_Startup": "/Game/Mods/FreightDock/BP_Startup"}
STARTUP_GRAPHS = {"RegisterFreightDock", "RegisterOptions", "RegisterExtras"}


def target(name):
    """The Blueprint ("BP_MapLoad" / "BP_Startup") that function `name` is installed into."""
    assert name in GRAPHS, f"unknown function {name}"
    return "BP_Startup" if name in STARTUP_GRAPHS else "BP_MapLoad"
