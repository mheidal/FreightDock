"""BP_Startup: RegisterFreightDock calls Loom (BPL_FDSetup.RegisterFreightDock): the freight dock building (a copy of
the trade dock's GridActor rows), its icon and its own unlock. Its strings are in BPL_FDText.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import EXEC, OBJ
from fdgen.core.paths import MODAPI, SETUP_LIB
from fdgen.core.nodes import get_self
from fdgen.core.specs import fn_spec


def register_freight_dock():
    """RegisterFreightDock (BP_Startup): BPL_FDSetup.RegisterFreightDock(ModAPI)."""
    g = Graph()
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 250)
    g.call("Call", SETUP_LIB, "RegisterFreightDock", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Api", "in", OBJ(MODAPI), None)])
    g.link(("GetModAPI", "ModAPI"), ("Call", "Api"))
    return g.render()


SPECS = {
    "RegisterFreightDock": fn_spec(("Call", "execute")),
}


GRAPHS = {
    "RegisterFreightDock": register_freight_dock,
}
