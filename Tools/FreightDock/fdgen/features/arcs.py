"""Arcs: voyage arcs, the selected pair's lavender arc (PairArcs), and the hovered stand-in's route (DrawArcs).
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import (
    BOOL, DOUBLE, EXEC, FLOAT, INT, INT_ARRAY_T, MAP_INT_ACTOR, MAP_INT_INT, MAP_INT_VECTOR,
    OBJ, STRUCT)
from fdgen.core.paths import ACTOR, ARCPLAN, COLOR, K2, MAPLIB, MATHLIB, PC, PCPLAY, STATICS, VECTOR, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, branch, comp_owner, for_each, get_local, get_member, get_self, int_op,
    is_valid, make_struct, map_find, set_local, set_self, user_call)
from fdgen.features.docks import dock_id_call
from fdgen.features.pairing import flip


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
    """Every frame (Event Tick, also while paused): the selected paired dock's route arc, and each voyage's arc
    (stand-in -> where it's heading) while the stand-in is hovered or its dock / partner is selected - plus, while
    it's hovered, one to its home dock and its course as the route line."""
    g = Graph()
    F = "DrawArcs"
    get_local(g, "GetSelDock", F, "SelDock", OBJ(WORKDOCK), 0, 600)
    get_local(g, "GetCursor", F, "Cursor", STRUCT(VECTOR), 0, 700)
    get_local(g, "GetSelId", F, "SelId", INT, 0, 800)
    get_local(g, "GetSelPartnerId", F, "SelPartnerId", INT, 0, 900)
    get_local(g, "GetPartner", F, "Partner", OBJ(WORKDOCK), 0, 1000)
    get_local(g, "GetId", F, "Id", INT, 0, 1100)
    get_local(g, "GetProxy", F, "Proxy", OBJ(ACTOR), 0, 1200)
    get_local(g, "GetPhase", F, "Phase", INT, 0, 1300)
    get_self(g, "GetRouteSelId", "RouteSelId", INT, 0, 1400)
    get_self(g, "GetRouteValid", "RouteValid", BOOL, 0, 1500)
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 0, 1800)
    get_self(g, "GetVHome", "VoyageHome", MAP_INT_VECTOR, 0, 1900)
    get_self(g, "GetVTarget", "VoyageTarget", MAP_INT_VECTOR, 0, 2000)
    get_self(g, "GetVPhase", "VoyagePhase", MAP_INT_INT, 0, 2100)
    get_self(g, "GetHover", "HoverRadius", DOUBLE, 0, 2200)

    # player controller (shared by every arc)
    g.call("GetPC", STATICS, "GetPlayerController", 250, 600,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ(PC), None)])
    g.node("CastPC", K2 + "K2Node_DynamicCast",
           [f"TargetType=\"/Script/CoreUObject.Class'{PCPLAY}'\"", "PureState=Pure"], 500, 600,
           [("Object", "in", OBJ(PC), None), ("AsPlayer Controller Play", "out", OBJ(PCPLAY), None),
            ("bSuccess", "out", BOOL, None)])
    g.link(("GetPC", "ReturnValue"), ("CastPC", "Object"))
    pc_play = ("CastPC", "AsPlayer Controller Play")

    # selected dock
    g.node("FindSel", K2 + "K2Node_CallFunction",
           ['FunctionReference=(MemberName="FindDockUnderCursor",bSelfContext=True)'], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Dock", "out", OBJ(WORKDOCK), None), ("HitLoc", "out", STRUCT(VECTOR), None)])
    set_local(g, "SetSelDock", F, "SelDock", OBJ(WORKDOCK), 250, 0)
    g.link(("FindSel", "then"), ("SetSelDock", "execute"))
    g.link(("FindSel", "Dock"), ("SetSelDock", "SelDock"))

    # cursor on the sea plane: mouse ray -> plane z = 0
    g.call("Deproject", f"/Script/CoreUObject.Class'{PC}'", "DeprojectMousePositionToWorld", 750, 600,
           [("self", "in", OBJ(PC), None), ("WorldLocation", "out", STRUCT(VECTOR), None),
            ("WorldDirection", "out", STRUCT(VECTOR), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetPC", "ReturnValue"), ("Deproject", "self"))
    g.call("RayLen", MATHLIB, "Multiply_VectorFloat", 1000, 700,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", DOUBLE, 'DefaultValue="10000000.0"'),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("Deproject", "WorldDirection"), ("RayLen", "A"))
    g.call("RayEnd", MATHLIB, "Add_VectorVector", 1250, 700,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("Deproject", "WorldLocation"), ("RayEnd", "A"))
    g.link(("RayLen", "ReturnValue"), ("RayEnd", "B"))
    g.call("SeaHit", MATHLIB, "LinePlaneIntersection_OriginNormal", 1500, 600,
           [("LineStart", "in", STRUCT(VECTOR), None), ("LineEnd", "in", STRUCT(VECTOR), None),
            ("PlaneOrigin", "in", STRUCT(VECTOR), 'DefaultValue="0.000000,0.000000,0.000000"'),
            ("PlaneNormal", "in", STRUCT(VECTOR), 'DefaultValue="0.000000,0.000000,1.000000"'),
            ("T", "out", FLOAT, None), ("Intersection", "out", STRUCT(VECTOR), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Deproject", "WorldLocation"), ("SeaHit", "LineStart"))
    g.link(("RayEnd", "ReturnValue"), ("SeaHit", "LineEnd"))
    set_local(g, "SetCursor", F, "Cursor", STRUCT(VECTOR), 500, 0)
    g.link(("SetSelDock", "then"), ("SetCursor", "execute"))
    g.link(("SeaHit", "Intersection"), ("SetCursor", "Cursor"))

    # selected dock's id and its partner's id (-999 when nothing is selected)
    is_valid(g, "SelOk", WORKDOCK, 750, 200)
    g.link(("GetSelDock", "SelDock"), ("SelOk", "Object"))
    branch(g, "BrSel", 750, 0)
    g.link(("SetCursor", "then"), ("BrSel", "execute"))
    g.link(("SelOk", "ReturnValue"), ("BrSel", "Condition"))
    set_local(g, "SetSelId", F, "SelId", INT, 1000, -100)
    g.link(("BrSel", "then"), ("SetSelId", "execute"))
    g.link(dock_id_call(g, "SelDockId", ("GetSelDock", "SelDock"), 1000, -250), ("SetSelId", "SelId"))
    get_member(g, "SelPartnerEnc", WORKDOCK, "activeTradePartnerId", INT, 1250, -250)
    g.link(("GetSelDock", "SelDock"), ("SelPartnerEnc", "self"))
    set_local(g, "SetSelPartnerId", F, "SelPartnerId", INT, 1250, -100)
    g.link(("SetSelId", "then"), ("SetSelPartnerId", "execute"))
    g.link(flip(g, "SelPartnerDec", ("SelPartnerEnc", "activeTradePartnerId"), 1500, -250), ("SetSelPartnerId", "SelPartnerId"))
    for name, var, y in (("ClearSelId", "SelId", 100), ("ClearSelPartnerId", "SelPartnerId", 100)):
        g.node(name, K2 + "K2Node_VariableSet", [local_var(F, var)], 1000 if name == "ClearSelId" else 1250, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                (var, "in", INT, 'DefaultValue="-999"'), ("Output_Get", "out", INT, None)])
    g.link(("BrSel", "else"), ("ClearSelId", "execute"))
    g.link(("ClearSelId", "then"), ("ClearSelPartnerId", "execute"))

    # route arc: recompute only when the selection changes (PartnerOf searches every actor)
    changed = int_op(g, "SelChanged", "NotEqual_IntInt", ("GetSelId", "SelId"), ("GetRouteSelId", "RouteSelId"), 1750, 200)
    branch(g, "BrChanged", 1750, 0)
    g.link(("SetSelPartnerId", "then"), ("BrChanged", "execute"))
    g.link(("ClearSelPartnerId", "then"), ("BrChanged", "execute"))
    g.link(changed, ("BrChanged", "Condition"))
    set_self(g, "SetRouteSelId", "RouteSelId", INT, 2000, -100)
    g.link(("BrChanged", "then"), ("SetRouteSelId", "execute"))
    g.link(("GetSelId", "SelId"), ("SetRouteSelId", "RouteSelId"))
    set_self(g, "ClearRouteValid", "RouteValid", BOOL, 2250, -100, literal="false")
    g.link(("SetRouteSelId", "then"), ("ClearRouteValid", "execute"))
    branch(g, "BrSel2", 2500, -100)
    g.link(("ClearRouteValid", "then"), ("BrSel2", "execute"))
    g.link(("SelOk", "ReturnValue"), ("BrSel2", "Condition"))
    user_call(g, "FindPartner", "PartnerOf", 2750, -100, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Partner", OBJ(WORKDOCK))])
    g.link(("BrSel2", "then"), ("FindPartner", "execute"))
    g.link(("GetSelDock", "SelDock"), ("FindPartner", "Dock"))
    set_local(g, "SetPartner", F, "Partner", OBJ(WORKDOCK), 3000, -100)
    g.link(("FindPartner", "then"), ("SetPartner", "execute"))
    g.link(("FindPartner", "Partner"), ("SetPartner", "Partner"))
    is_valid(g, "PartnerOk", WORKDOCK, 3250, 50)
    g.link(("GetPartner", "Partner"), ("PartnerOk", "Object"))
    branch(g, "BrPartner", 3250, -100)
    g.link(("SetPartner", "then"), ("BrPartner", "execute"))
    g.link(("PartnerOk", "ReturnValue"), ("BrPartner", "Condition"))
    comp_owner(g, "SelOwner", WORKDOCK, 3500, 100)
    g.link(("GetSelDock", "SelDock"), ("SelOwner", "self"))
    actor_loc(g, "SelLoc", ("SelOwner", "ReturnValue"), 3750, 100)
    comp_owner(g, "PartnerOwner", WORKDOCK, 3500, 200)
    g.link(("GetPartner", "Partner"), ("PartnerOwner", "self"))
    actor_loc(g, "PartnerLoc", ("PartnerOwner", "ReturnValue"), 3750, 200)
    set_self(g, "SetRouteStart", "RouteStart", STRUCT(VECTOR), 3500, -100)
    g.link(("BrPartner", "then"), ("SetRouteStart", "execute"))
    g.link(("SelLoc", "ReturnValue"), ("SetRouteStart", "RouteStart"))
    set_self(g, "SetRouteEnd", "RouteEnd", STRUCT(VECTOR), 3750, -100)
    g.link(("SetRouteStart", "then"), ("SetRouteEnd", "execute"))
    g.link(("PartnerLoc", "ReturnValue"), ("SetRouteEnd", "RouteEnd"))
    set_self(g, "SetRouteValid", "RouteValid", BOOL, 4000, -100, literal="true")
    g.link(("SetRouteEnd", "then"), ("SetRouteValid", "execute"))

    branch(g, "BrRoute", 4250, 0)
    for src in (("SetRouteValid", "then"), ("BrPartner", "else"), ("BrSel2", "else"), ("BrChanged", "else")):
        g.link(src, ("BrRoute", "execute"))
    g.link(("GetRouteValid", "RouteValid"), ("BrRoute", "Condition"))
    user_call(g, "Route", "DrawRoute", 4500, -100, ins=[("Id", INT), ("PC", OBJ(PCPLAY))])
    g.link(("BrRoute", "then"), ("Route", "execute"))
    g.link(("GetRouteSelId", "RouteSelId"), ("Route", "Id"))
    g.link(pc_play, ("Route", "PC"))
    route_done = ("Route", "then")

    # voyage arcs
    g.call("Keys", MAPLIB, "Map_Keys", 4750, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", MAP_INT_ACTOR, None), ("Keys", "out", INT_ARRAY_T, None)])
    g.link(route_done, ("Keys", "execute"))
    g.link(("BrRoute", "else"), ("Keys", "execute"))
    g.link(("GetVoyages", "Voyages"), ("Keys", "TargetMap"))
    for_each(g, "ForIds", INT, 5000, 0)
    g.link(("Keys", "then"), ("ForIds", "Exec"))
    g.link(("Keys", "Keys"), ("ForIds", "Array"))
    set_local(g, "SetId", F, "Id", INT, 5300, 0)
    g.link(("ForIds", "LoopBody"), ("SetId", "execute"))
    g.link(("ForIds", "Array Element"), ("SetId", "Id"))
    key = ("GetId", "Id")
    map_find(g, "FindProxy", ("GetVoyages", "Voyages"), key, MAP_INT_ACTOR, OBJ(ACTOR), 5300, 200, key_type=INT)
    set_local(g, "SetProxy", F, "Proxy", OBJ(ACTOR), 5550, 0)
    g.link(("SetId", "then"), ("SetProxy", "execute"))
    g.link(("FindProxy", "Value"), ("SetProxy", "Proxy"))
    map_find(g, "FindPhase", ("GetVPhase", "VoyagePhase"), key, MAP_INT_INT, INT, 5550, 200, key_type=INT)
    set_local(g, "SetPhase", F, "Phase", INT, 5800, 0)
    g.link(("SetProxy", "then"), ("SetPhase", "execute"))
    g.link(("FindPhase", "Value"), ("SetPhase", "Phase"))

    is_valid(g, "ProxyOk", ACTOR, 6050, 200)
    g.link(("GetProxy", "Proxy"), ("ProxyOk", "Object"))
    branch(g, "BrProxy", 6050, 0)
    g.link(("SetPhase", "then"), ("BrProxy", "execute"))
    g.link(("ProxyOk", "ReturnValue"), ("BrProxy", "Condition"))

    actor_loc(g, "Pos", ("GetProxy", "Proxy"), 6050, 400)
    map_find(g, "FindTarget", ("GetVTarget", "VoyageTarget"), key, MAP_INT_VECTOR, STRUCT(VECTOR), 6050, 550, key_type=INT)
    map_find(g, "FindHome", ("GetVHome", "VoyageHome"), key, MAP_INT_VECTOR, STRUCT(VECTOR), 6050, 700, key_type=INT)
    going_home = int_op(g, "GoingHome", "GreaterEqual_IntInt", ("GetPhase", "Phase"), None, 6050, 850, b_default="2")
    g.call("Dest", MATHLIB, "SelectVector", 6300, 600,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("FindHome", "Value"), ("Dest", "A"))
    g.link(("FindTarget", "Value"), ("Dest", "B"))
    g.link(going_home, ("Dest", "bPickA"))

    g.call("CursorDist", MATHLIB, "Vector_Distance2D", 6300, 400,
           [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetCursor", "Cursor"), ("CursorDist", "v1"))
    g.link(("Pos", "ReturnValue"), ("CursorDist", "v2"))
    g.call("Hovered", MATHLIB, "LessEqual_DoubleDouble", 6550, 400,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("CursorDist", "ReturnValue"), ("Hovered", "A"))
    g.link(("GetHover", "HoverRadius"), ("Hovered", "B"))
    is_sel = int_op(g, "IsSel", "EqualEqual_IntInt", key, ("GetSelId", "SelId"), 6300, 950)
    is_sel_p = int_op(g, "IsSelPartner", "EqualEqual_IntInt", key, ("GetSelPartnerId", "SelPartnerId"), 6300, 1100)
    g.call("AnySel", MATHLIB, "BooleanOR", 6550, 1000,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(is_sel, ("AnySel", "A"))
    g.link(is_sel_p, ("AnySel", "B"))
    g.call("Highlight", MATHLIB, "BooleanOR", 6800, 700,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Hovered", "ReturnValue"), ("Highlight", "A"))
    g.link(("AnySel", "ReturnValue"), ("Highlight", "B"))
    branch(g, "BrArc", 6300, 0)
    g.link(("BrProxy", "then"), ("BrArc", "execute"))
    g.link(("Highlight", "ReturnValue"), ("BrArc", "Condition"))
    after_v = queue_arc(g, "V", pc_play, ("Pos", "ReturnValue"), ("Dest", "ReturnValue"), ("BrArc", "then"), 6550, -100)
    # while hovered, also one to its home dock
    branch(g, "BrHomeArc", 6800, -100)
    g.link(after_v, ("BrHomeArc", "execute"))
    g.link(("Hovered", "ReturnValue"), ("BrHomeArc", "Condition"))
    after_h = queue_arc(g, "H", pc_play, ("Pos", "ReturnValue"), ("FindHome", "Value"), ("BrHomeArc", "then"), 7050, -100)
    # ... and its route line (DrawRoute after the selected dock's, so the hovered ship's course wins)
    user_call(g, "HoverRoute", "DrawRoute", 7300, -100, ins=[("Id", INT), ("PC", OBJ(PCPLAY))])
    g.link(after_h, ("HoverRoute", "execute"))
    g.link(key, ("HoverRoute", "Id"))
    g.link(pc_play, ("HoverRoute", "PC"))
    # dock-to-partner arcs
    user_call(g, "Pairs", "PairArcs", 5300, -300, ins=[("PC", OBJ(PCPLAY))])
    g.link(("ForIds", "Completed"), ("Pairs", "execute"))
    g.link(pc_play, ("Pairs", "PC"))
    return g.render()


def pair_arcs():
    """PairArcs(PC): while a paired dock is selected, an arc in PairArcColor / PairArcHeight from it to its partner
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
    "DrawArcs": fn_spec(("FindSel", "execute"),
                        locals_=[("SelDock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK)), ("Cursor", STRUCT(VECTOR)), ("SelId", INT),
                                 ("SelPartnerId", INT), ("Id", INT), ("Phase", INT), ("Proxy", OBJ(ACTOR))]),
    "PairArcs": fn_spec(("BrSel", "execute"), inputs=[("PC", OBJ(PCPLAY))]),
}


GRAPHS = {
    "DrawArcs": draw_arcs,
    "PairArcs": pair_arcs,
}
