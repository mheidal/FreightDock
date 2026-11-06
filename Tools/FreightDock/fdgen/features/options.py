"""Strings, Mod Options and the per-tick hook, all calling Loom: RegisterOptions (BP_Startup) -> BPL_FDText.Register
(all of the mod's strings; the options themselves are registered by BP_MainMenuLoad); ReadPairKey (BeginPlay and
whenever an option changes) -> BPL_FDOptions; PairKeyTick (Event Tick) -> BPL_FDPairing.Tick
(stand-in clicks, the panel). The names are kept from the pairing key, which the panel's network picker replaced:
the hand-built Event Graph calls them.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import EXEC, OBJ
from fdgen.core.paths import MODAPI, OPTIONS_LIB, PAIRING_LIB, TEXT_LIB
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import get_self, loom_call


def register_options():
    """RegisterOptions (BP_Startup; the name is kept, the hand-built Event Graph calls it): BPL_FDText.Register(ModAPI)
    - every FreightDock string, in one AddNewStrings call. The Mod Options are registered by BP_MainMenuLoad."""
    g = Graph()
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 250)
    g.call("Call", TEXT_LIB, "Register", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Api", "in", OBJ(MODAPI), None)])
    g.link(("GetModAPI", "ModAPI"), ("Call", "Api"))
    return g.render()


def read_pair_key():
    """ReadPairKey: BPL_FDOptions.ReadOptions - MaxWaitSeconds from the "Depart after" option."""
    g = Graph()
    loom_call(g, "Call", OPTIONS_LIB, "ReadOptions", 0, 0)
    return g.render()


def pair_key_tick():
    """PairKeyTick (Event Tick, also while paused): BPL_FDPairing.Tick - StandInClick, then PanelTick.
    (DebugCells, the F7 cell overlay, is not called: hook it in there while debugging routes.)"""
    g = Graph()
    loom_call(g, "Call", PAIRING_LIB, "Tick", 0, 0)
    return g.render()


SPECS = {
    "RegisterOptions": fn_spec(("Call", "execute")),
    "ReadPairKey": fn_spec(("Call", "execute")),
    "PairKeyTick": fn_spec(("Call", "execute")),
}


GRAPHS = {
    "RegisterOptions": register_options,
    "ReadPairKey": read_pair_key,
    "PairKeyTick": pair_key_tick,
}
