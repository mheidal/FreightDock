"""A* over route cells (FindPath) and PlanRoute, which plans one dock's route to its target.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, EXEC, INT, INT_ARRAY, INT_SET, MAP_INT_INT, MAP_INT_VECTOR, OBJ, STRUCT, VEC_ARRAY
from fdgen.core.paths import MAPLIB, MATHLIB, MODAPI, VECTOR, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    arr_item, arrfn, bnot, bop, branch, chain, for_each, for_loop, get_local, get_self, ii,
    is_valid, map_add, set_add, set_clear, set_contains, set_local, set_pin_default, set_self, user_call)
from fdgen.core.text import fmt_to_string, log_msg
from fdgen.features.docks import dock_id_call
from fdgen.routes.cells import KEY_MUL, cell_key_call, cell_pos_call, near_end, octile


def find_path():
    """FindPath(Start, Goal) -> Found: A* over route cells avoiding Blocked; fills PathCells (start .. goal).
    Locals: StartKey, GoalKey, Best, Cur (Integer); Open, OpenF (Integer arrays); G, Came (Integer -> Integer maps);
    Closed (Set of Integer); Done (Boolean). Wire node "GetDoneForReturn" to the Return node's Found."""
    g = Graph()
    F = "FindPath"
    L = lambda name, var, t, x, y: get_local(g, name, F, var, t, x, y)
    L("GetStart", "Start", STRUCT(VECTOR), 0, 600)
    L("GetGoal", "Goal", STRUCT(VECTOR), 0, 700)
    L("GetStartKey", "StartKey", INT, 0, 800)
    L("GetGoalKey", "GoalKey", INT, 0, 900)
    L("GetBest", "Best", INT, 0, 1000)
    L("GetCur", "Cur", INT, 0, 1100)
    L("GetOpen", "Open", INT_ARRAY, 0, 1200)
    L("GetOpenF", "OpenF", INT_ARRAY, 0, 1300)
    L("GetG", "G", MAP_INT_INT, 0, 1400)
    L("GetCame", "Came", MAP_INT_INT, 0, 1500)
    L("GetClosed", "Closed", INT_SET, 0, 1600)
    L("GetDone", "Done", BOOL, 0, 1700)
    get_self(g, "GetBlocked", "Blocked", INT_SET, 0, 1800)
    get_self(g, "GetPath", "PathCells", INT_ARRAY, 0, 1900)
    get_self(g, "GetMax", "MaxExpand", INT, 0, 2000)
    start_key, goal_key = ("GetStartKey", "StartKey"), ("GetGoalKey", "GoalKey")
    best = ("GetBest", "Best")

    # init
    set_local(g, "SetStartKey", F, "StartKey", INT, 0, 0)
    g.link(cell_key_call(g, "StartCell", ("GetStart", "Start"), 0, 300), ("SetStartKey", "StartKey"))
    set_local(g, "SetGoalKey", F, "GoalKey", INT, 250, 0)
    g.link(cell_key_call(g, "GoalCell", ("GetGoal", "Goal"), 250, 300), ("SetGoalKey", "GoalKey"))
    seq = ["SetStartKey", "SetGoalKey"]
    for name, src, t in (("ClearOpen", ("GetOpen", "Open"), INT_ARRAY), ("ClearOpenF", ("GetOpenF", "OpenF"), INT_ARRAY),
                         ("ClearPath", ("GetPath", "PathCells"), INT_ARRAY)):
        arrfn(g, name, "Array_Clear", 250 * len(seq), 0,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", t, None)])
        g.link(src, (name, "TargetArray"))
        seq.append(name)
    for name, src in (("ClearG", ("GetG", "G")), ("ClearCame", ("GetCame", "Came"))):
        g.call(name, MAPLIB, "Map_Clear", 250 * len(seq), 0,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_INT_INT, None)])
        g.link(src, (name, "TargetMap"))
        seq.append(name)
    set_clear(g, "ClearClosed", ("GetClosed", "Closed"), 250 * len(seq), 0)
    seq.append("ClearClosed")
    set_local(g, "DoneFalse", F, "Done", BOOL, 250 * len(seq), 0)
    set_pin_default(g, "DoneFalse", "Done", "false")
    seq.append("DoneFalse")

    def push(prefix, key_src, f_src, x, y):
        arrfn(g, prefix + "Open", "Array_Add", x, y,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", INT_ARRAY, None),
               ("NewItem", "in", INT, None), ("ReturnValue", "out", INT, None)])
        g.link(("GetOpen", "Open"), (prefix + "Open", "TargetArray"))
        g.link(key_src, (prefix + "Open", "NewItem"))
        arrfn(g, prefix + "OpenF", "Array_Add", x + 250, y,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", INT_ARRAY, None),
               ("NewItem", "in", INT, None), ("ReturnValue", "out", INT, None)])
        g.link(("GetOpenF", "OpenF"), (prefix + "OpenF", "TargetArray"))
        g.link(f_src, (prefix + "OpenF", "NewItem"))
        g.link((prefix + "Open", "then"), (prefix + "OpenF", "execute"))
        return prefix + "Open", prefix + "OpenF"

    x0 = 250 * len(seq)
    h0 = octile(g, "H0", start_key, goal_key, x0, 400)
    a, b = push("Push0", start_key, h0, x0, 0)
    seq.append(a)
    map_add(g, "G0", ("GetG", "G"), start_key, None, MAP_INT_INT, INT, x0 + 500, 0, key_type=INT)
    set_pin_default(g, "G0", "Value", "0")
    chain(g, *seq)
    g.link((b, "then"), ("G0", "execute"))

    # main loop
    X = x0 + 800
    for_loop(g, "Loop", X, 0, first=0, with_break=True)
    g.link(("GetMax", "MaxExpand"), ("Loop", "LastIndex"))
    g.link(("G0", "then"), ("Loop", "Exec"))
    arrfn(g, "OpenLen", "Array_Length", X, 300,
          [("TargetArray", "in", INT_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetOpen", "Open"), ("OpenLen", "TargetArray"))
    empty = ii(g, "Empty", "EqualEqual_IntInt", ("OpenLen", "ReturnValue"), None, X + 250, 300, b_default="0", out=BOOL)
    branch(g, "BrEmpty", X + 250, 0)
    g.link(("Loop", "LoopBody"), ("BrEmpty", "execute"))
    g.link(empty, ("BrEmpty", "Condition"))
    g.link(("BrEmpty", "then"), ("Loop", "Break"))

    g.call("MinF", MATHLIB, "MinOfIntArray", X + 250, 450,
           [("IntArray", "in", INT_ARRAY, None), ("IndexOfMinValue", "out", INT, None), ("MinValue", "out", INT, None)])
    g.link(("GetOpenF", "OpenF"), ("MinF", "IntArray"))
    idx = ("MinF", "IndexOfMinValue")
    set_local(g, "SetBest", F, "Best", INT, X + 500, 0)
    g.link(("BrEmpty", "else"), ("SetBest", "execute"))
    g.link(arr_item(g, "OpenAtMin", ("GetOpen", "Open"), idx, INT, X + 500, 450), ("SetBest", "Best"))
    for i, (name, src) in enumerate((("PopOpen", ("GetOpen", "Open")), ("PopOpenF", ("GetOpenF", "OpenF")))):
        arrfn(g, name, "Array_Remove", X + 750 + 250 * i, 0,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", INT_ARRAY, None),
               ("IndexToRemove", "in", INT, None)])
        g.link(src, (name, "TargetArray"))
        g.link(idx, (name, "IndexToRemove"))
    chain(g, "SetBest", "PopOpen", "PopOpenF")
    at_goal = ii(g, "AtGoal", "EqualEqual_IntInt", best, goal_key, X + 1250, 300, out=BOOL)
    branch(g, "BrGoal", X + 1250, 0)
    g.link(("PopOpenF", "then"), ("BrGoal", "execute"))
    g.link(at_goal, ("BrGoal", "Condition"))
    set_local(g, "DoneTrue", F, "Done", BOOL, X + 1500, -200)
    set_pin_default(g, "DoneTrue", "Done", "true")
    g.link(("BrGoal", "then"), ("DoneTrue", "execute"))
    g.link(("DoneTrue", "then"), ("Loop", "Break"))
    was_closed = set_contains(g, "WasClosed", ("GetClosed", "Closed"), best, X + 1500, 300)
    branch(g, "BrClosed", X + 1500, 0)
    g.link(("BrGoal", "else"), ("BrClosed", "execute"))
    g.link(was_closed, ("BrClosed", "Condition"))
    set_add(g, "Close", ("GetClosed", "Closed"), best, X + 1750, 0)
    g.link(("BrClosed", "else"), ("Close", "execute"))

    # neighbours
    for_loop(g, "ForDX", X + 2000, 0, first=-1, last=1)
    for_loop(g, "ForDY", X + 2250, 0, first=-1, last=1)
    g.link(("Close", "then"), ("ForDX", "Exec"))
    g.link(("ForDX", "LoopBody"), ("ForDY", "Exec"))
    dxo = ii(g, "DXOff", "Multiply_IntInt", ("ForDX", "Index"), None, X + 2000, 300, b_default=KEY_MUL)
    nb = ii(g, "NbA", "Add_IntInt", best, dxo, X + 2250, 300)
    nb = ii(g, "Nb", "Add_IntInt", nb, ("ForDY", "Index"), X + 2500, 300)
    not_self = ii(g, "NotSelf", "NotEqual_IntInt", nb, best, X + 2750, 300, out=BOOL)
    not_closed = bnot(g, "NotClosed", set_contains(g, "NbClosed", ("GetClosed", "Closed"), nb, X + 2750, 450), X + 3000, 450)
    free = bnot(g, "Free", set_contains(g, "NbBlocked", ("GetBlocked", "Blocked"), nb, X + 2750, 600), X + 3000, 600)
    is_goal = ii(g, "NbGoal", "EqualEqual_IntInt", nb, goal_key, X + 2750, 750, out=BOOL)
    near = near_end(g, "E", cell_pos_call(g, "NbPos", nb, X + 2750, 2000), X + 3000, 2000)
    passable = bop(g, "Passable0", "BooleanOR", free, is_goal, X + 3250, 650)
    passable = bop(g, "Passable", "BooleanOR", passable, near, X + 3500, 700)
    ok = bop(g, "Ok1", "BooleanAND", not_self, not_closed, X + 3250, 350)
    ok = bop(g, "Ok", "BooleanAND", ok, passable, X + 3500, 450)
    branch(g, "BrOk", X + 2500, 0)
    g.link(("ForDY", "LoopBody"), ("BrOk", "execute"))
    g.link(ok, ("BrOk", "Condition"))

    # tentative cost: G[Best] + 14 diagonal / 10 straight
    g.call("GBest", MAPLIB, "Map_Find", X + 3500, 900,
           [("TargetMap", "in", MAP_INT_INT, None), ("Key", "in", INT, None), ("Value", "out", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetG", "G"), ("GBest", "TargetMap"))
    g.link(best, ("GBest", "Key"))
    diag = ii(g, "DXY", "Multiply_IntInt", ("ForDX", "Index"), ("ForDY", "Index"), X + 3250, 1050)
    is_diag = ii(g, "IsDiag", "NotEqual_IntInt", diag, None, X + 3500, 1050, b_default="0", out=BOOL)
    g.call("StepCost", MATHLIB, "SelectInt", X + 3750, 1050,
           [("A", "in", INT, 'DefaultValue="14"'), ("B", "in", INT, 'DefaultValue="10"'), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", INT, None)])
    g.link(is_diag, ("StepCost", "bPickA"))
    get_self(g, "GetPenalty", "Penalty", MAP_INT_INT, X + 3500, 1150)
    g.call("NbPen", MAPLIB, "Map_Find", X + 3750, 1150,
           [("TargetMap", "in", MAP_INT_INT, None), ("Key", "in", INT, None), ("Value", "out", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetPenalty", "Penalty"), ("NbPen", "TargetMap"))
    g.link(nb, ("NbPen", "Key"))
    pen_cost = ii(g, "PenCost", "Multiply_IntInt", ("NbPen", "Value"), None, X + 4000, 1150, b_default="10")
    step = ii(g, "StepTotal", "Add_IntInt", ("StepCost", "ReturnValue"), pen_cost, X + 4000, 1050)
    tent = ii(g, "Tent", "Add_IntInt", ("GBest", "Value"), step, X + 4250, 950)
    g.call("GNb", MAPLIB, "Map_Find", X + 3750, 1250,
           [("TargetMap", "in", MAP_INT_INT, None), ("Key", "in", INT, None), ("Value", "out", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetG", "G"), ("GNb", "TargetMap"))
    g.link(nb, ("GNb", "Key"))
    unseen = bnot(g, "Unseen", ("GNb", "ReturnValue"), X + 4000, 1250)
    cheaper = ii(g, "Cheaper", "Less_IntInt", tent, ("GNb", "Value"), X + 4250, 1150, out=BOOL)
    better = bop(g, "Better", "BooleanOR", unseen, cheaper, X + 4500, 1200)
    branch(g, "BrBetter", X + 2750, 0)
    g.link(("BrOk", "then"), ("BrBetter", "execute"))
    g.link(better, ("BrBetter", "Condition"))
    map_add(g, "SetG", ("GetG", "G"), nb, tent, MAP_INT_INT, INT, X + 3000, 0, key_type=INT)
    map_add(g, "SetCame", ("GetCame", "Came"), nb, best, MAP_INT_INT, INT, X + 3250, 0, key_type=INT)
    hn = octile(g, "HN", nb, goal_key, X + 4500, 1400)
    fn = ii(g, "FN", "Add_IntInt", tent, hn, X + 5000, 1000)
    a, _ = push("PushNb", nb, fn, X + 3500, 0)
    chain(g, "BrBetter", "SetG", "SetCame")
    g.link(("SetCame", "then"), (a, "execute"))

    # path: walk Came back from the goal
    branch(g, "BrFound", X, -500)
    g.link(("Loop", "Completed"), ("BrFound", "execute"))
    g.link(("GetDone", "Done"), ("BrFound", "Condition"))
    set_local(g, "CurGoal", F, "Cur", INT, X + 250, -500)
    g.link(("BrFound", "then"), ("CurGoal", "execute"))
    g.link(goal_key, ("CurGoal", "Cur"))
    for_loop(g, "Walk", X + 500, -500, first=0, with_break=True)
    g.link(("GetMax", "MaxExpand"), ("Walk", "LastIndex"))
    g.link(("CurGoal", "then"), ("Walk", "Exec"))
    arrfn(g, "Prepend", "Array_Insert", X + 750, -500,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", INT_ARRAY, None),
           ("NewItem", "in", INT, None), ("Index", "in", INT, 'DefaultValue="0"')])
    g.link(("Walk", "LoopBody"), ("Prepend", "execute"))
    g.link(("GetPath", "PathCells"), ("Prepend", "TargetArray"))
    g.link(("GetCur", "Cur"), ("Prepend", "NewItem"))
    at_start = ii(g, "AtStart", "EqualEqual_IntInt", ("GetCur", "Cur"), start_key, X + 1000, -300, out=BOOL)
    branch(g, "BrStart", X + 1000, -500)
    g.link(("Prepend", "then"), ("BrStart", "execute"))
    g.link(at_start, ("BrStart", "Condition"))
    g.link(("BrStart", "then"), ("Walk", "Break"))
    g.call("Back", MAPLIB, "Map_Find", X + 1250, -300,
           [("TargetMap", "in", MAP_INT_INT, None), ("Key", "in", INT, None), ("Value", "out", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetCame", "Came"), ("Back", "TargetMap"))
    g.link(("GetCur", "Cur"), ("Back", "Key"))
    set_local(g, "CurBack", F, "Cur", INT, X + 1250, -500)
    g.link(("BrStart", "else"), ("CurBack", "execute"))
    g.link(("Back", "Value"), ("CurBack", "Cur"))
    L("GetDoneForReturn", "Done", BOOL, X, -700)
    return g.render()


def plan_route():
    """PlanRoute(Dock): water route from Dock's stand-off point to its target's, stored as RoutePts[Id*1000+i]
    and RouteLen[Id], and logged. Straight if the direct line is clear.
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
    arrfn(g, "CellsLen", "Array_Length", 6250, -550, [("TargetArray", "in", INT_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetPath", "PathCells"), ("CellsLen", "TargetArray"))
    s = fmt_to_string(g, "FmtLog", "Route for dock {id}: {n} points ({cells} path cells; 0 = straight line)",
                      [("id", INT), ("n", INT), ("cells", INT)], 6500, -550)
    g.link(("GetId", "Id"), ("FmtLog", "id"))
    g.link(("PtsLen", "ReturnValue"), ("FmtLog", "n"))
    g.link(("CellsLen", "ReturnValue"), ("FmtLog", "cells"))
    log_msg(g, "LogRoute", "GetModAPI", 6250, -250)
    g.link(("StoreLen", "then"), ("LogRoute", "execute"))
    g.link((s, "ReturnValue"), ("LogRoute", "Msg"))
    user_call(g, "DropCurve", "DropRouteCurve", 6500, -250, ins=[("Id", INT)])
    g.link(("LogRoute", "then"), ("DropCurve", "execute"))
    g.link(("GetId", "Id"), ("DropCurve", "Id"))
    return g.render()


SPECS = {
    "PlanRoute": fn_spec(("SetId", "execute"), inputs=[("Dock", OBJ(WORKDOCK))],
                         locals_=[("Start", STRUCT(VECTOR)), ("Goal", STRUCT(VECTOR)), ("Anchor", STRUCT(VECTOR)),
                                  ("Prev", STRUCT(VECTOR)), ("Pts", VEC_ARRAY), ("Id", INT)]),
}


GRAPHS = {
    "FindPath": find_path,
    "PlanRoute": plan_route,
}
