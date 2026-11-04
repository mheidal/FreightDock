"""Deliver now: DeliverSelected, called by the Freight Dock panel's button (WBP_FDPanel), backdates the selected dock's
loading clock so the ship departs.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, DOUBLE, EXEC, INT, MAP_INT_ACTOR, MAP_INT_DOUBLE, OBJ, STRUCT
from fdgen.core.paths import K2, MAPLIB, MODAPI, VECTOR, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import branch, get_self, is_valid, map_add, map_find, set_pin_default
from fdgen.core.text import fmt_to_string, log_msg, toast
from fdgen.features.docks import dock_id_call


def deliver_selected():
    """DeliverSelected (the panel's Deliver now button): the selected freight dock's ship sails now with what it has - its
    loading clock (LoadingSince) is set far back so FreightTick's max-wait check passes. Ship away (in Voyages) or
    nothing loaded yet: a toast."""
    g = Graph()
    F = "DeliverSelected"
    get_self(g, "GetSince", "LoadingSince", MAP_INT_DOUBLE, 0, 400)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 500)
    g.node("FindSel", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="FindDockUnderCursor",bSelfContext=True)'], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Dock", "out", OBJ(WORKDOCK), None), ("HitLoc", "out", STRUCT(VECTOR), None)])
    is_valid(g, "SelOk", WORKDOCK, 250, 300)
    g.link(("FindSel", "Dock"), ("SelOk", "Object"))
    branch(g, "BrSel", 250, 0)
    g.link(("FindSel", "then"), ("BrSel", "execute"))
    g.link(("SelOk", "ReturnValue"), ("BrSel", "Condition"))
    did = dock_id_call(g, "SelId", ("FindSel", "Dock"), 250, 450)
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 0, 600)
    g.call("Away", MAPLIB, "Map_Contains", 500, 600,
           [("TargetMap", "in", MAP_INT_ACTOR, None), ("Key", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetVoyages", "Voyages"), ("Away", "TargetMap"))
    g.link(did, ("Away", "Key"))
    branch(g, "BrAway", 400, 0)
    g.link(("BrSel", "then"), ("BrAway", "execute"))
    g.link(("Away", "ReturnValue"), ("BrAway", "Condition"))
    toast(g, "UnderWay", 500, -250, literal="The ship is under way")
    g.link(("BrAway", "then"), ("UnderWay", "execute"))
    map_find(g, "Clock", ("GetSince", "LoadingSince"), did, MAP_INT_DOUBLE, DOUBLE, 500, 400, key_type=INT)
    branch(g, "BrLoading", 500, 0)
    g.link(("BrAway", "else"), ("BrLoading", "execute"))
    g.link(("Clock", "ReturnValue"), ("BrLoading", "Condition"))
    map_add(g, "Backdate", ("GetSince", "LoadingSince"), did, None, MAP_INT_DOUBLE, DOUBLE, 750, -100, key_type=INT)
    set_pin_default(g, "Backdate", "Value", "-1000000000000000.0")
    g.link(("BrLoading", "then"), ("Backdate", "execute"))
    s = fmt_to_string(g, "FmtDeliver", "Deliver now: dock {d}", [("d", INT)], 750, 300)
    g.link(did, ("FmtDeliver", "d"))
    log_msg(g, "Log", "GetModAPI", 1000, -100)
    g.link(("Backdate", "then"), ("Log", "execute"))
    g.link((s, "ReturnValue"), ("Log", "Msg"))
    toast(g, "Nothing", 750, 150, literal="Nothing loaded yet")
    g.link(("BrLoading", "else"), ("Nothing", "execute"))
    return g.render()


SPECS = {
    "DeliverSelected": fn_spec(("FindSel", "execute")),
}


GRAPHS = {
    "DeliverSelected": deliver_selected,
}
