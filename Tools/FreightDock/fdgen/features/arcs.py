"""Arcs: the selected pair's lavender arc (PairArcs). DrawArcs (voyage arcs, the hovered stand-in's route) is in Loom
(BPL_FDPairing); its graph only calls it.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, EXEC, FLOAT, OBJ, STRUCT
from fdgen.core.paths import ARCPLAN, COLOR, PAIRING_LIB, PCPLAY, VECTOR
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import branch, get_local, get_self, loom_call, make_struct


def queue_arc(g, p, cast_pin, start_src, end_src, after, x, y, height_var="ArcHeight", color_var="ArcColor"):
    """Make an ArcPlan (color_var / ArcWidth / height_var) from start to end and queue it for this frame."""
    get_self(g, p + "Color", color_var, STRUCT(COLOR), x, y + 300)
    get_self(g, p + "Width", "ArcWidth", FLOAT, x, y + 400)
    get_self(g, p + "Height", height_var, FLOAT, x, y + 500)
    make_struct(g, p + "Make", ARCPLAN,
                [("worldStart", STRUCT(VECTOR)), ("worldEnd", STRUCT(VECTOR)), ("Color", STRUCT(COLOR)),
                 ("linewidthTop", FLOAT), ("linewidthEnd", FLOAT), ("arcHeightRatioOfLength", FLOAT)], x + 250, y + 300)
    g.link(start_src, (p + "Make", "worldStart"))
    g.link(end_src, (p + "Make", "worldEnd"))
    g.link((p + "Color", color_var), (p + "Make", "Color"))
    g.link((p + "Width", "ArcWidth"), (p + "Make", "linewidthTop"))
    g.link((p + "Width", "ArcWidth"), (p + "Make", "linewidthEnd"))
    g.link((p + "Height", height_var), (p + "Make", "arcHeightRatioOfLength"))
    g.call(p + "Queue", f"/Script/CoreUObject.Class'{PCPLAY}'", "QueueSynchronizedArcPlanForFrame", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(PCPLAY), None),
            ("plan", "in", STRUCT(ARCPLAN), None)])
    g.link(after, (p + "Queue", "execute"))
    g.link(cast_pin, (p + "Queue", "self"))
    g.link((p + "Make", "ArcPlan"), (p + "Queue", "plan"))
    return (p + "Queue", "then")


def draw_arcs():
    """DrawArcs (every frame, also while paused): BPL_FDPairing.DrawArcs - the selected paired dock's route arc, voyage
    arcs, the hovered stand-in's course, then PairArcs."""
    g = Graph()
    loom_call(g, "Call", PAIRING_LIB, "DrawArcs", 0, 0)
    return g.render()


def pair_arcs():
    """PairArcs(PC): while a paired dock is selected, an arc in PairArcColor / PairArcHeight from it to its target
    (RouteStart -> RouteEnd, kept by DrawArcs)."""
    g = Graph()
    F = "PairArcs"
    get_local(g, "GetPC", F, "PC", OBJ(PCPLAY), 0, 400)
    get_self(g, "GetRouteValid", "RouteValid", BOOL, 0, 500)
    get_self(g, "GetRouteStart", "RouteStart", STRUCT(VECTOR), 0, 600)
    get_self(g, "GetRouteEnd", "RouteEnd", STRUCT(VECTOR), 0, 700)
    branch(g, "BrSel", 0, 0)
    g.link(("GetRouteValid", "RouteValid"), ("BrSel", "Condition"))
    queue_arc(g, "S", ("GetPC", "PC"), ("GetRouteStart", "RouteStart"), ("GetRouteEnd", "RouteEnd"), ("BrSel", "then"),
              250, -100, height_var="PairArcHeight", color_var="PairArcColor")
    return g.render()


SPECS = {
    "DrawArcs": fn_spec(("Call", "execute")),
    "PairArcs": fn_spec(("BrSel", "execute"), inputs=[("PC", OBJ(PCPLAY))]),
}


GRAPHS = {
    "DrawArcs": draw_arcs,
    "PairArcs": pair_arcs,
}
