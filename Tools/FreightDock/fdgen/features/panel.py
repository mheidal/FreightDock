"""The Freight Dock panel (WBP_FDPanel, written in Loom: Content/Mods/FreightDock/UI/WBP_FDPanel.lm): PanelTick
creates it once and hands it every frame to its Step, which shows, places, fills and hides it.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import CLASSPIN, EXEC, INT, OBJ
from fdgen.core.paths import FD_PANEL_CLASS, K2, PC, STATICS, USERWIDGET
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import branch, get_self, is_valid, set_self


MAPLOAD_C = "/Game/Mods/FreightDock/BP_MapLoad.BP_MapLoad_C"
PANEL = f"/Script/UMG.WidgetBlueprintGeneratedClass'{FD_PANEL_CLASS}'"
PANEL_OBJ = ['PinType.PinCategory="object"', f'PinType.PinSubCategoryObject="{PANEL}"']
PANEL_ZORDER = "20"


def panel_tick():
    """PanelTick (from PairKeyTick, every frame, also while paused): make the panel the first time (CreateWidget,
    AddToViewport, stored in FDPanel), then FDPanel.Step(self)."""
    g = Graph()
    get_self(g, "GetPanel", "FDPanel", PANEL_OBJ, 0, 300)
    is_valid(g, "PanelOk", FD_PANEL_CLASS, 250, 300)
    g.link(("GetPanel", "FDPanel"), ("PanelOk", "Object"))
    branch(g, "BrHas", 0, 0)
    g.link(("PanelOk", "ReturnValue"), ("BrHas", "Condition"))

    g.call("PCForWidget", STATICS, "GetPlayerController", 250, 300,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ(PC), None)])
    wct, wcd = CLASSPIN(USERWIDGET, FD_PANEL_CLASS)
    g.node("Make", "/Script/UMGEditor.K2Node_CreateWidget", [], 250, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Class", "in", wct, wcd),
            ("OwningPlayer", "in", OBJ(PC), None), ("ReturnValue", "out", PANEL_OBJ, None)])
    g.link(("BrHas", "else"), ("Make", "execute"))
    g.link(("PCForWidget", "ReturnValue"), ("Make", "OwningPlayer"))
    set_self(g, "SetPanel", "FDPanel", PANEL_OBJ, 500, 150)
    g.link(("Make", "then"), ("SetPanel", "execute"))
    g.link(("Make", "ReturnValue"), ("SetPanel", "FDPanel"))
    g.call("Show", f"/Script/CoreUObject.Class'{USERWIDGET}'", "AddToViewport", 750, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(USERWIDGET), None),
            ("ZOrder", "in", INT, f'DefaultValue="{PANEL_ZORDER}"')])
    g.link(("SetPanel", "then"), ("Show", "execute"))
    g.link(("Make", "ReturnValue"), ("Show", "self"))

    g.node("Self", K2 + "K2Node_Self", [], 1000, 300, [("self", "out", ['PinType.PinCategory="object"', 'PinType.PinSubCategory="self"'], None)])
    get_self(g, "GetPanelForStep", "FDPanel", PANEL_OBJ, 1000, 450)
    g.call("Step", PANEL, "Step", 1250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", PANEL_OBJ, None),
            ("Owner", "in", OBJ(MAPLOAD_C), None)])
    g.link(("BrHas", "then"), ("Step", "execute"))
    g.link(("Show", "then"), ("Step", "execute"))
    g.link(("GetPanelForStep", "FDPanel"), ("Step", "self"))
    g.link(("Self", "self"), ("Step", "Owner"))
    return g.render()


SPECS = {
    "PanelTick": fn_spec(("BrHas", "execute")),
}


GRAPHS = {
    "PanelTick": panel_tick,
}
