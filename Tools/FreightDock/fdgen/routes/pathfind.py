"""A* over route cells (FindPath) and PlanRoute, which plans one dock's route to its target.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, EXEC, INT, INT_ARRAY, INT_SET, MAP_INT_INT, MAP_INT_VECTOR, OBJ, STRUCT, VEC_ARRAY
from fdgen.core.paths import MAPLIB, MATHLIB, MODAPI, VECTOR, VOYAGE_LIB, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    arr_item, arrfn, bnot, bop, branch, chain, for_each, for_loop, get_local, get_self, ii,
    is_valid, loom_call, map_add, set_add, set_clear, set_contains, set_local, set_pin_default, set_self, user_call)
from fdgen.core.text import fmt_to_string, log_msg
from fdgen.features.docks import dock_id_call
from fdgen.routes.cells import KEY_MUL, cell_key_call, cell_pos_call, near_end, octile


def find_path():
    """FindPath(Start, Goal) -> Found: BPL_FDVoyage.FindPath - A* over route cells (blocked cells, other docks'
    outlines and corner cuts avoided, near-shore cells costly); fills PathCells (start .. goal)."""
    g = Graph()
    get_local(g, "GetStart", "FindPath", "Start", STRUCT(VECTOR), 0, 250)
    get_local(g, "GetGoal", "FindPath", "Goal", STRUCT(VECTOR), 0, 350)
    loom_call(g, "Call", VOYAGE_LIB, "FindPath", 250, 0, ins=[("Start", STRUCT(VECTOR)), ("Goal", STRUCT(VECTOR))],
              outs=[("ReturnValue", BOOL)])
    g.link(("GetStart", "Start"), ("Call", "Start"))
    g.link(("GetGoal", "Goal"), ("Call", "Goal"))
    return g.render()


def plan_route():
    """PlanRoute(Dock): water route from Dock's stand-off point to its target's, stored as RoutePts[Id*1000+i]
    and RouteLen[Id]. Straight if the direct line is clear.
    Locals: Start, Goal, Anchor, Prev (Vector); Pts (Vector array); Id (Integer)."""
    g = Graph()
    F = "PlanRoute"
    L = lambda name, var, t, x, y: get_local(g, name, F, var, t, x, y)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 1500)
    L("GetDock", "Dock", OBJ(WORKDOCK), 0, 600)
    L("GetStart", "Start", STRUCT(VECTOR), 0, 700)
    L("GetGoal", "Goal", STRUCT(VECTOR), 0, 800)
    L("GetAnchor", "Anchor", STRUCT(VECTOR), 0, 900)
    L("GetPrev", "Prev", STRUCT(VECTOR), 0, 1000)
    L("GetPts", "Pts", VEC_ARRAY, 0, 1100)
    L("GetId", "Id", INT, 0, 1200)
    get_self(g, "GetPath", "PathCells", INT_ARRAY, 0, 1300)
    get_self(g, "GetRoutePts", "RoutePts", MAP_INT_VECTOR, 0, 1400)
    get_self(g, "GetRouteLen", "RouteLen", MAP_INT_INT, 0, 1600)
    pts = ("GetPts", "Pts")

    set_local(g, "SetId", F, "Id", INT, 0, 0)
    g.link(dock_id_call(g, "DockId", ("GetDock", "Dock"), 0, 300), ("SetId", "Id"))
    user_call(g, "Target", "TargetOf", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Target", OBJ(WORKDOCK))])
    g.link(("GetDock", "Dock"), ("Target", "Dock"))
    is_valid(g, "TargetOk", WORKDOCK, 500, 300)
    g.link(("Target", "Target"), ("TargetOk", "Object"))
    branch(g, "BrTarget", 500, 0)
    g.link(("TargetOk", "ReturnValue"), ("BrTarget", "Condition"))
    log_msg(g, "LogNoTarget", "GetModAPI", 750, 300, literal="PlanRoute: the selected dock has no target")
    g.link(("BrTarget", "else"), ("LogNoTarget", "execute"))
    user_call(g, "HomeStand", "StandOffPoint", 750, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Pos", STRUCT(VECTOR))])
    g.link(("GetDock", "Dock"), ("HomeStand", "Dock"))
    set_local(g, "SetStart", F, "Start", STRUCT(VECTOR), 1000, 0)
    g.link(("HomeStand", "Pos"), ("SetStart", "Start"))
    user_call(g, "AwayStand", "StandOffPoint", 1250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Pos", STRUCT(VECTOR))])
    g.link(("Target", "Target"), ("AwayStand", "Dock"))
    set_local(g, "SetGoal", F, "Goal", STRUCT(VECTOR), 1500, 0)
    g.link(("AwayStand", "Pos"), ("SetGoal", "Goal"))
    arrfn(g, "ClearPts", "Array_Clear", 1750, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None)])
    g.link(pts, ("ClearPts", "TargetArray"))
    arrfn(g, "ClearPath", "Array_Clear", 2000, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", INT_ARRAY, None)])
    g.link(("GetPath", "PathCells"), ("ClearPath", "TargetArray"))

    def add_pt(name, src, x, y):
        arrfn(g, name, "Array_Add", x, y,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None),
               ("NewItem", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", INT, None)])
        g.link(pts, (name, "TargetArray"))
        g.link(src, (name, "NewItem"))
        return name

    add_pt("AddStart", ("GetStart", "Start"), 2250, 0)
    chain(g, "SetId", "Target", "BrTarget")
    g.link(("BrTarget", "then"), ("HomeStand", "execute"))
    # the ends, for the near-dock clearance exemption in ClearLine / FindPath
    set_self(g, "SetPlanStart", "PlanStart", STRUCT(VECTOR), 1600, -200)
    g.link(("GetStart", "Start"), ("SetPlanStart", "PlanStart"))
    set_self(g, "SetPlanGoal", "PlanGoal", STRUCT(VECTOR), 1700, -200)
    g.link(("GetGoal", "Goal"), ("SetPlanGoal", "PlanGoal"))
    chain(g, "HomeStand", "SetStart", "AwayStand", "SetGoal", "SetPlanStart", "SetPlanGoal", "ClearPts", "ClearPath", "AddStart")

    def clear_line_call(name, a, b, x, y):
        user_call(g, name, "ClearLine", x, y, ins=[("A", STRUCT(VECTOR)), ("B", STRUCT(VECTOR))], outs=[("LineClear", BOOL)])
        g.link(a, (name, "A"))
        g.link(b, (name, "B"))
        return name

    clear_line_call("Direct", ("GetStart", "Start"), ("GetGoal", "Goal"), 2500, 0)
    g.link(("AddStart", "then"), ("Direct", "execute"))
    branch(g, "BrDirect", 2750, 0)
    g.link(("Direct", "then"), ("BrDirect", "execute"))
    g.link(("Direct", "LineClear"), ("BrDirect", "Condition"))
    user_call(g, "Search", "FindPath", 3000, 200, ins=[("Start", STRUCT(VECTOR)), ("Goal", STRUCT(VECTOR))], outs=[("Found", BOOL)])
    g.link(("BrDirect", "else"), ("Search", "execute"))
    g.link(("GetStart", "Start"), ("Search", "Start"))
    g.link(("GetGoal", "Goal"), ("Search", "Goal"))
    branch(g, "BrFound", 3250, 200)
    g.link(("Search", "then"), ("BrFound", "execute"))
    g.link(("Search", "Found"), ("BrFound", "Condition"))
    log_msg(g, "LogNoRoute", "GetModAPI", 3500, 500, literal="PlanRoute: no water route found within MaxExpand - using a straight line")
    g.link(("BrFound", "else"), ("LogNoRoute", "execute"))

    # pull the string: keep a cell only where the line from the last kept point can't reach the next one
    set_local(g, "AnchorStart", F, "Anchor", STRUCT(VECTOR), 3500, 200)
    g.link(("BrFound", "then"), ("AnchorStart", "execute"))
    g.link(("GetStart", "Start"), ("AnchorStart", "Anchor"))
    set_local(g, "PrevStart", F, "Prev", STRUCT(VECTOR), 3750, 200)
    g.link(("AnchorStart", "then"), ("PrevStart", "execute"))
    g.link(("GetStart", "Start"), ("PrevStart", "Prev"))
    for_each(g, "ForCells", INT, 4000, 200)
    g.link(("PrevStart", "then"), ("ForCells", "Exec"))
    g.link(("GetPath", "PathCells"), ("ForCells", "Array"))
    c = cell_pos_call(g, "CellAt", ("ForCells", "Array Element"), 4000, 500)
    clear_line_call("Sees", ("GetAnchor", "Anchor"), c, 4250, 200)
    g.link(("ForCells", "LoopBody"), ("Sees", "execute"))
    branch(g, "BrSees", 4500, 200)
    g.link(("Sees", "then"), ("BrSees", "execute"))
    g.link(("Sees", "LineClear"), ("BrSees", "Condition"))
    add_pt("KeepPrev", ("GetPrev", "Prev"), 4750, 400)
    g.link(("BrSees", "else"), ("KeepPrev", "execute"))
    set_local(g, "AnchorPrev", F, "Anchor", STRUCT(VECTOR), 5000, 400)
    g.link(("KeepPrev", "then"), ("AnchorPrev", "execute"))
    g.link(("GetPrev", "Prev"), ("AnchorPrev", "Anchor"))
    set_local(g, "PrevCell", F, "Prev", STRUCT(VECTOR), 5250, 200)
    g.link(("BrSees", "then"), ("PrevCell", "execute"))
    g.link(("AnchorPrev", "then"), ("PrevCell", "execute"))
    g.link(c, ("PrevCell", "Prev"))
    clear_line_call("SeesGoal", ("GetAnchor", "Anchor"), ("GetGoal", "Goal"), 4250, -100)
    g.link(("ForCells", "Completed"), ("SeesGoal", "execute"))
    branch(g, "BrSeesGoal", 4500, -100)
    g.link(("SeesGoal", "then"), ("BrSeesGoal", "execute"))
    g.link(("SeesGoal", "LineClear"), ("BrSeesGoal", "Condition"))
    add_pt("KeepLast", ("GetPrev", "Prev"), 4750, -100)
    g.link(("BrSeesGoal", "else"), ("KeepLast", "execute"))

    # finish: goal, store, log, draw
    add_pt("AddGoal", ("GetGoal", "Goal"), 5500, -100)
    for src in (("BrDirect", "then"), ("LogNoRoute", "then"), ("BrSeesGoal", "then"), ("KeepLast", "then")):
        g.link(src, ("AddGoal", "execute"))
    for_each(g, "ForPts", STRUCT(VECTOR), 5750, -100)
    g.link(("AddGoal", "then"), ("ForPts", "Exec"))
    g.link(pts, ("ForPts", "Array"))
    base = ii(g, "Base", "Multiply_IntInt", ("GetId", "Id"), None, 5750, 200, b_default="1000")
    slot = ii(g, "Slot", "Add_IntInt", base, ("ForPts", "Array Index"), 6000, 200)
    map_add(g, "StorePt", ("GetRoutePts", "RoutePts"), slot, ("ForPts", "Array Element"), MAP_INT_VECTOR, STRUCT(VECTOR),
            6000, -100, key_type=INT)
    g.link(("ForPts", "LoopBody"), ("StorePt", "execute"))
    arrfn(g, "PtsLen", "Array_Length", 6000, -400, [("TargetArray", "in", VEC_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(pts, ("PtsLen", "TargetArray"))
    map_add(g, "StoreLen", ("GetRouteLen", "RouteLen"), ("GetId", "Id"), ("PtsLen", "ReturnValue"), MAP_INT_INT, INT,
            6000, -250, key_type=INT)
    g.link(("ForPts", "Completed"), ("StoreLen", "execute"))
    user_call(g, "DropCurve", "DropRouteCurve", 6500, -250, ins=[("Id", INT)])
    g.link(("StoreLen", "then"), ("DropCurve", "execute"))
    g.link(("GetId", "Id"), ("DropCurve", "Id"))
    return g.render()


SPECS = {
    "FindPath": fn_spec(("Call", "execute"), inputs=[("Start", STRUCT(VECTOR)), ("Goal", STRUCT(VECTOR))],
                        outputs=[("Found", BOOL)], returns=[("Call", "then")], values=[("Call", "ReturnValue", "Found")]),
    "PlanRoute": fn_spec(("SetId", "execute"), inputs=[("Dock", OBJ(WORKDOCK))],
                         locals_=[("Start", STRUCT(VECTOR)), ("Goal", STRUCT(VECTOR)), ("Anchor", STRUCT(VECTOR)),
                                  ("Prev", STRUCT(VECTOR)), ("Pts", VEC_ARRAY), ("Id", INT)]),
}


GRAPHS = {
    "FindPath": find_path,
    "PlanRoute": plan_route,
}
