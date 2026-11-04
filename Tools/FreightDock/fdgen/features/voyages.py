"""Voyages: StartVoyage spawns the stand-in and course, VoyageTick moves it along the spline (moored / sailing /
waiting phases), VoyageArrive unloads (with goods flying to the dock, BP_FDFling) and returns the ship.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import (
    BOOL, CLASSPIN, COLLISION_PIN, DOUBLE, EXEC, FLOAT, INT, INT_ARRAY_T, MAP_INT_ACTOR,
    MAP_INT_DOUBLE, MAP_INT_INT, MAP_INT_OBJ, MAP_INT_SHIP, MAP_INT_VECTOR, OBJ, SPLINE_SPACE, STRUCT)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, CHILDCOMP, FD_FLING_CLASS, HIT, K2, MAPLIB, MATHLIB, MODAPI, NDOCK, NDOCKSTATE,
    ROTATOR, SHIP, SHIPSTATE, SPLINE, SYSLIB, TRANSFORM, VECTOR, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, bnot, bop, branch, break_struct, clear_timer, dmath, dmath1, for_each,
    get_local, get_member, get_self, int_op, is_valid, map_add, map_find, map_remove, set_local, set_pin_default,
    start_timer, user_call)
from fdgen.core.text import fmt_to_string, log_msg
from fdgen.features.docks import dock_id_call
from fdgen.features.standins import PROXY_YAW, bob_pose, set_hidden, zoomed_child


VOYAGE_TICK = "0.016000"    # ~60 steps per second (game time)


def start_voyage():
    """Spawn a stand-in from Ship's zoomed-in model, hide the real ship, and sail the stand-in to Partner's berth."""
    g = Graph()
    F = "StartVoyage"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 500)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 600)
    get_local(g, "GetPartner", F, "Partner", OBJ(WORKDOCK), 0, 700)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 800)
    get_local(g, "GetId", F, "Id", INT, 0, 900)
    get_local(g, "GetProxy", F, "Proxy", OBJ(ACTOR), 0, 1000)
    get_local(g, "GetTarget", F, "Target", OBJ(NDOCK), 0, 1100)
    ship = ("GetShip", "Ship")
    key = ("GetId", "Id")

    set_local(g, "SetId", F, "Id", INT, 0, 0)
    g.link(dock_id_call(g, "DockId", ("GetDock", "Dock"), 0, 250), ("SetId", "Id"))
    user_call(g, "FindTarget", "NauticalDockAt", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Best", OBJ(NDOCK))])
    g.link(("SetId", "then"), ("FindTarget", "execute"))
    g.link(("GetPartner", "Partner"), ("FindTarget", "Dock"))
    set_local(g, "SetTarget", F, "Target", OBJ(NDOCK), 500, 0)
    g.link(("FindTarget", "then"), ("SetTarget", "execute"))
    g.link(("FindTarget", "Best"), ("SetTarget", "Target"))

    zoomed, child = zoomed_child(g, "Z", ship, 500, 300)
    is_valid(g, "ChildOk", ACTOR, 750, 400)
    g.link(child, ("ChildOk", "Object"))
    is_valid(g, "TargetOk", NDOCK, 750, 500)
    g.link(("GetTarget", "Target"), ("TargetOk", "Object"))
    g.call("BothOk", MATHLIB, "BooleanAND", 1000, 450,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("ChildOk", "ReturnValue"), ("BothOk", "A"))
    g.link(("TargetOk", "ReturnValue"), ("BothOk", "B"))
    branch(g, "BrOk", 750, 0)
    g.link(("SetTarget", "then"), ("BrOk", "execute"))
    g.link(("BothOk", "ReturnValue"), ("BrOk", "Condition"))
    log_msg(g, "LogFail", "GetModAPI", 1000, 150,
            literal="StartVoyage: no ship model or partner berth - falling back to the timed trip")
    g.link(("BrOk", "else"), ("LogFail", "execute"))

    ctype, _ = CLASSPIN(ACTOR, ACTOR)
    get_member(g, "ChildCls", CHILDCOMP, "ChildActorClass", ctype, 1000, 600)
    g.link(zoomed, ("ChildCls", "self"))
    g.call("ChildXform", f"/Script/CoreUObject.Class'{ACTOR}'", "GetTransform", 1000, 700,
           [("self", "in", OBJ(ACTOR), None), ("ReturnValue", "out", STRUCT(TRANSFORM), None)])
    g.link(child, ("ChildXform", "self"))
    g.node("Spawn", K2 + "K2Node_SpawnActorFromClass", [], 1000, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Class", "in", ctype, None), ("ReturnValue", "out", OBJ(ACTOR), None),
            ("SpawnTransform", "in", STRUCT(TRANSFORM), None),
            ("CollisionHandlingOverride", "in", COLLISION_PIN, 'DefaultValue="AlwaysSpawn"'),
            ("Owner", "in", OBJ(ACTOR), None)])
    g.link(("BrOk", "then"), ("Spawn", "execute"))
    g.link(("ChildCls", "ChildActorClass"), ("Spawn", "Class"))
    g.link(("ChildXform", "ReturnValue"), ("Spawn", "SpawnTransform"))
    set_local(g, "SetProxy", F, "Proxy", OBJ(ACTOR), 1250, 0)
    g.link(("Spawn", "then"), ("SetProxy", "execute"))
    g.link(("Spawn", "ReturnValue"), ("SetProxy", "Proxy"))
    set_hidden(g, "HideShip", ship, True, 1500, 0)
    g.link(("SetProxy", "then"), ("HideShip", "execute"))
    set_hidden(g, "HideChild", child, True, 1750, 0)
    g.link(("HideShip", "then"), ("HideChild", "execute"))

    # home = the stand-in's start; target = (berth X, berth Y, home Z)
    actor_loc(g, "Home", ("GetProxy", "Proxy"), 1750, 600)
    get_member(g, "TargetState", NDOCK, "State", STRUCT(NDOCKSTATE), 1750, 300)
    g.link(("GetTarget", "Target"), ("TargetState", "self"))
    break_struct(g, "BreakTarget", NDOCKSTATE,
                 [("berthLocation", STRUCT(VECTOR)), ("berthOutDirection", STRUCT(VECTOR))], 2000, 300)
    get_self(g, "GetStandOff", "StandOff", DOUBLE, 2000, 450)
    g.call("OutStep", MATHLIB, "Multiply_VectorFloat", 2250, 450,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("BreakTarget", "berthOutDirection"), ("OutStep", "A"))
    g.link(("GetStandOff", "StandOff"), ("OutStep", "B"))
    g.call("StandPos", MATHLIB, "Add_VectorVector", 2500, 450,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("BreakTarget", "berthLocation"), ("StandPos", "A"))
    g.link(("OutStep", "ReturnValue"), ("StandPos", "B"))
    g.link(("TargetState", "State"), ("BreakTarget", "NauticalDockState"))
    g.call("BerthXYZ", MATHLIB, "BreakVector", 2250, 300,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None),
            ("Z", "out", DOUBLE, None)])
    g.link(("StandPos", "ReturnValue"), ("BerthXYZ", "InVec"))
    g.call("HomeXYZ", MATHLIB, "BreakVector", 2000, 600,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None),
            ("Z", "out", DOUBLE, None)])
    g.link(("Home", "ReturnValue"), ("HomeXYZ", "InVec"))
    g.call("Dest", MATHLIB, "MakeVector", 2500, 400,
           [("X", "in", DOUBLE, None), ("Y", "in", DOUBLE, None), ("Z", "in", DOUBLE, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("BerthXYZ", "X"), ("Dest", "X"))
    g.link(("BerthXYZ", "Y"), ("Dest", "Y"))
    g.link(("HomeXYZ", "Z"), ("Dest", "Z"))

    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 2000, -300)
    get_self(g, "GetVShip", "VoyageShip", MAP_INT_SHIP, 2000, -400)
    get_self(g, "GetVHome", "VoyageHome", MAP_INT_VECTOR, 2000, -500)
    get_self(g, "GetVTarget", "VoyageTarget", MAP_INT_VECTOR, 2000, -600)
    get_self(g, "GetVPhase", "VoyagePhase", MAP_INT_INT, 2000, -700)
    prev = ("HideChild", "then")
    for i, (name, mp, mtype, vtype, val) in enumerate((
            ("AddVoyage", ("GetVoyages", "Voyages"), MAP_INT_ACTOR, OBJ(ACTOR), ("GetProxy", "Proxy")),
            ("AddShip", ("GetVShip", "VoyageShip"), MAP_INT_SHIP, OBJ(SHIP), ship),
            ("AddHome", ("GetVHome", "VoyageHome"), MAP_INT_VECTOR, STRUCT(VECTOR), ("Home", "ReturnValue")),
            ("AddTarget", ("GetVTarget", "VoyageTarget"), MAP_INT_VECTOR, STRUCT(VECTOR), ("Dest", "ReturnValue")),
            ("AddPhase", ("GetVPhase", "VoyagePhase"), MAP_INT_INT, INT, None))):
        map_add(g, name, mp, key, val, mtype, vtype, 2250 + 250 * i, 0, key_type=INT)
        g.link(prev, (name, "execute"))
        prev = (name, "then")
    set_pin_default(g, "AddPhase", "Value", "1")    # outbound
    get_self(g, "GetVBerth", "VoyageBerth", MAP_INT_OBJ(NDOCK), 2000, -800)
    get_member(g, "ShipStateNow", SHIP, "State", STRUCT(SHIPSTATE), 3500, 300)
    g.link(ship, ("ShipStateNow", "self"))
    break_struct(g, "BreakShipNow", SHIPSTATE, [("dockedDock", OBJ(NDOCK))], 3750, 300)
    g.link(("ShipStateNow", "State"), ("BreakShipNow", "NauticalShipState"))
    map_add(g, "AddBerth", ("GetVBerth", "VoyageBerth"), key, ("BreakShipNow", "dockedDock"), MAP_INT_OBJ(NDOCK), OBJ(NDOCK),
            3500, 0, key_type=INT)
    g.link(prev, ("AddBerth", "execute"))
    get_self(g, "GetVPartner", "VoyagePartner", MAP_INT_INT, 2000, -900)
    map_add(g, "AddPartner", ("GetVPartner", "VoyagePartner"), key, dock_id_call(g, "PartnerId", ("GetPartner", "Partner"), 3750, 450),
            MAP_INT_INT, INT, 3750, 0, key_type=INT)
    g.link(("AddBerth", "then"), ("AddPartner", "execute"))
    # the course: MakeCourse builds the outbound spline (any previous one for this dock is dropped first)
    X = 4000
    get_self(g, "GetVSpline", "VoyageSpline", MAP_INT_OBJ(SPLINE), 2000, -1000)
    get_self(g, "GetVDist", "VoyageDist", MAP_INT_DOUBLE, 2000, -1100)
    map_find(g, "OldSpline", ("GetVSpline", "VoyageSpline"), key, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), X, 300, key_type=INT)
    is_valid(g, "OldOk", SPLINE, X + 250, 300)
    g.link(("OldSpline", "Value"), ("OldOk", "Object"))
    branch(g, "BrOld", X, 0)
    g.link(("AddPartner", "then"), ("BrOld", "execute"))
    g.link(("OldOk", "ReturnValue"), ("BrOld", "Condition"))
    g.call("DropOld", f"/Script/CoreUObject.Class'{ACTORCOMP}'", "K2_DestroyComponent", X + 250, -150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTORCOMP), None),
            ("Object", "in", OBJ("/Script/CoreUObject.Object"), None)])
    g.link(("BrOld", "then"), ("DropOld", "execute"))
    g.link(("OldSpline", "Value"), ("DropOld", "self"))
    user_call(g, "Course", "MakeCourse", X + 500, 0,
              ins=[("Id", INT), ("Ship", OBJ(SHIP)), ("ToHome", BOOL)], outs=[("Course", OBJ(SPLINE))])
    g.link(("BrOld", "else"), ("Course", "execute"))
    g.link(("DropOld", "then"), ("Course", "execute"))
    g.link(key, ("Course", "Id"))
    g.link(ship, ("Course", "Ship"))
    set_pin_default(g, "Course", "ToHome", "false")
    map_add(g, "AddSpline", ("GetVSpline", "VoyageSpline"), key, ("Course", "Course"), MAP_INT_OBJ(SPLINE), OBJ(SPLINE),
            X + 750, 0, key_type=INT)
    g.link(("Course", "then"), ("AddSpline", "execute"))
    map_add(g, "AddDist", ("GetVDist", "VoyageDist"), key, None, MAP_INT_DOUBLE, DOUBLE, X + 1000, 0, key_type=INT)
    set_pin_default(g, "AddDist", "Value", "0.0")
    g.link(("AddSpline", "then"), ("AddDist", "execute"))
    start_timer(g, "StartTick", "VoyageTick", VOYAGE_TICK, X + 1250, 0)
    g.link(("AddDist", "then"), ("StartTick", "execute"))
    return g.render()


def voyage_tick():
    """Timer target: move every stand-in; handle the wait at the partner and hand arrivals to VoyageArrive.
    A stand-in turns in place (at TurnRate) at the start of a course until it faces along it, and at the end until
    it faces VoyageEndFwd, before it counts as arrived - so its heading never jumps. It bobs like a moored ship
    (StandInBob), sailing or waiting; TurnRate only steers its yaw, so the bob's tilt doesn't build up."""
    g = Graph()
    F = "VoyageTick"
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 0, 400)
    get_self(g, "GetVPhase", "VoyagePhase", MAP_INT_INT, 0, 700)
    get_self(g, "GetVWait", "VoyageWait", MAP_INT_DOUBLE, 0, 800)
    get_self(g, "GetSpeed", "ShipSpeed", DOUBLE, 0, 900)
    get_local(g, "GetId", F, "Id", INT, 0, 1000)
    get_local(g, "GetProxy", F, "Proxy", OBJ(ACTOR), 0, 1100)
    get_local(g, "GetPhase", F, "Phase", INT, 0, 1200)
    key = ("GetId", "Id")
    proxy = ("GetProxy", "Proxy")

    # no voyages left: stop the timer
    g.call("Count", MAPLIB, "Map_Length", 0, 250,
           [("TargetMap", "in", MAP_INT_ACTOR, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetVoyages", "Voyages"), ("Count", "TargetMap"))
    none_left = int_op(g, "NoneLeft", "EqualEqual_IntInt", ("Count", "ReturnValue"), None, 250, 250, b_default="0")
    branch(g, "BrNone", 0, 0)
    g.link(none_left, ("BrNone", "Condition"))
    clear_timer(g, "StopTick", "VoyageTick", 250, 0)
    g.link(("BrNone", "then"), ("StopTick", "execute"))

    g.call("Keys", MAPLIB, "Map_Keys", 250, -300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", MAP_INT_ACTOR, None), ("Keys", "out", INT_ARRAY_T, None)])
    g.link(("BrNone", "else"), ("Keys", "execute"))
    g.link(("GetVoyages", "Voyages"), ("Keys", "TargetMap"))
    for_each(g, "ForIds", INT, 500, -300)
    g.link(("Keys", "then"), ("ForIds", "Exec"))
    g.link(("Keys", "Keys"), ("ForIds", "Array"))
    set_local(g, "SetId", F, "Id", INT, 800, -300)
    g.link(("ForIds", "LoopBody"), ("SetId", "execute"))
    g.link(("ForIds", "Array Element"), ("SetId", "Id"))
    map_find(g, "FindProxy", ("GetVoyages", "Voyages"), key, MAP_INT_ACTOR, OBJ(ACTOR), 800, -100, key_type=INT)
    set_local(g, "SetProxy", F, "Proxy", OBJ(ACTOR), 1050, -300)
    g.link(("SetId", "then"), ("SetProxy", "execute"))
    g.link(("FindProxy", "Value"), ("SetProxy", "Proxy"))
    map_find(g, "FindPhase", ("GetVPhase", "VoyagePhase"), key, MAP_INT_INT, INT, 1050, -100, key_type=INT)
    set_local(g, "SetPhase", F, "Phase", INT, 1300, -300)
    g.link(("SetProxy", "then"), ("SetPhase", "execute"))
    g.link(("FindPhase", "Value"), ("SetPhase", "Phase"))

    # phase 2: wait at the partner, then turn for home (phase 3)
    waiting = int_op(g, "IsWaiting", "EqualEqual_IntInt", ("GetPhase", "Phase"), None, 1550, -100, b_default="2")
    branch(g, "BrWaiting", 1550, -300)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 1300)
    get_self(g, "GetVShip", "VoyageShip", MAP_INT_SHIP, 0, 1400)
    map_find(g, "GFindShip", ("GetVShip", "VoyageShip"), key, MAP_INT_SHIP, OBJ(SHIP), 1300, -1000, key_type=INT)
    is_valid(g, "GShipOk", SHIP, 1550, -1000)
    g.link(("GFindShip", "Value"), ("GShipOk", "Object"))
    get_member(g, "GShipState", SHIP, "State", STRUCT(SHIPSTATE), 1550, -900)
    g.link(("GFindShip", "Value"), ("GShipState", "self"))
    break_struct(g, "GBreak", SHIPSTATE, [("dockedDock", OBJ(NDOCK))], 1800, -900)
    g.link(("GShipState", "State"), ("GBreak", "NauticalShipState"))
    get_self(g, "GetVBerth", "VoyageBerth", MAP_INT_OBJ(NDOCK), 0, 1500)
    map_find(g, "GFindBerth", ("GetVBerth", "VoyageBerth"), key, MAP_INT_OBJ(NDOCK), OBJ(NDOCK), 1800, -800, key_type=INT)
    g.call("GDockedOk", MATHLIB, "EqualEqual_ObjectObject", 2050, -900,
           [("A", "in", OBJ(NDOCK), None), ("B", "in", OBJ(NDOCK), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GBreak", "dockedDock"), ("GDockedOk", "A"))
    g.link(("GFindBerth", "Value"), ("GDockedOk", "B"))
    g.call("GBerthed", MATHLIB, "BooleanAND", 2050, -1000,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GShipOk", "ReturnValue"), ("GBerthed", "A"))
    g.link(("GDockedOk", "ReturnValue"), ("GBerthed", "B"))
    branch(g, "BrBerthed", 1300, -300)
    g.link(("SetPhase", "then"), ("BrBerthed", "execute"))
    g.link(("GBerthed", "ReturnValue"), ("BrBerthed", "Condition"))
    g.link(("BrBerthed", "then"), ("BrWaiting", "execute"))
    is_valid(g, "GProxyOk", ACTOR, 1550, -1150)
    g.link(proxy, ("GProxyOk", "Object"))
    branch(g, "BrGProxy", 1550, -1300)
    g.link(("BrBerthed", "else"), ("BrGProxy", "execute"))
    g.link(("GProxyOk", "ReturnValue"), ("BrGProxy", "Condition"))
    g.call("GDestroy", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_DestroyActor", 1800, -1300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None)])
    g.link(("BrGProxy", "then"), ("GDestroy", "execute"))
    g.link(proxy, ("GDestroy", "self"))
    s = fmt_to_string(g, "GFmt", "Dock {d}: ship left its berth - voyage cancelled, freight stays aboard",
                      [("d", INT)], 2050, -1450)
    g.link(key, ("GFmt", "d"))
    log_msg(g, "GLog", "GetModAPI", 2050, -1300)
    g.link(("GDestroy", "then"), ("GLog", "execute"))
    g.link(("BrGProxy", "else"), ("GLog", "execute"))
    g.link((s, "ReturnValue"), ("GLog", "Msg"))
    user_call(g, "GArrive", "VoyageArrive", 2300, -1300, ins=[("Id", INT)])
    g.link(("GLog", "then"), ("GArrive", "execute"))
    g.link(key, ("GArrive", "Id"))
    g.link(waiting, ("BrWaiting", "Condition"))
    g.call("Now", SYSLIB, "GetGameTimeInSeconds", 1800, -600, [("ReturnValue", "out", DOUBLE, None)])
    map_find(g, "FindWait", ("GetVWait", "VoyageWait"), key, MAP_INT_DOUBLE, DOUBLE, 1800, -500, key_type=INT)
    g.call("WaitDone", MATHLIB, "GreaterEqual_DoubleDouble", 2050, -550,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Now", "ReturnValue"), ("WaitDone", "A"))
    g.link(("FindWait", "Value"), ("WaitDone", "B"))
    branch(g, "BrWaitDone", 1800, -800)
    g.link(("BrWaiting", "then"), ("BrWaitDone", "execute"))
    g.link(("WaitDone", "ReturnValue"), ("BrWaitDone", "Condition"))
    map_add(g, "TurnHome", ("GetVPhase", "VoyagePhase"), key, None, MAP_INT_INT, INT, 2050, -800, key_type=INT)
    g.link(("BrWaitDone", "then"), ("TurnHome", "execute"))
    set_pin_default(g, "TurnHome", "Value", "3")
    # homeward course: drop the outbound spline, build one ending at the berth, start it from 0
    get_self(g, "GetVSpline2", "VoyageSpline", MAP_INT_OBJ(SPLINE), 2050, -1600)
    get_self(g, "GetVDist2", "VoyageDist", MAP_INT_DOUBLE, 2050, -1700)
    map_find(g, "OutSpline", ("GetVSpline2", "VoyageSpline"), key, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), 2300, -650, key_type=INT)
    g.call("DropOut", f"/Script/CoreUObject.Class'{ACTORCOMP}'", "K2_DestroyComponent", 2300, -800,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTORCOMP), None),
            ("Object", "in", OBJ("/Script/CoreUObject.Object"), None)])
    g.link(("TurnHome", "then"), ("DropOut", "execute"))
    g.link(("OutSpline", "Value"), ("DropOut", "self"))
    user_call(g, "HomeCourse", "MakeCourse", 2550, -800,
              ins=[("Id", INT), ("Ship", OBJ(SHIP)), ("ToHome", BOOL)], outs=[("Course", OBJ(SPLINE))])
    g.link(("DropOut", "then"), ("HomeCourse", "execute"))
    g.link(key, ("HomeCourse", "Id"))
    g.link(("GFindShip", "Value"), ("HomeCourse", "Ship"))
    set_pin_default(g, "HomeCourse", "ToHome", "true")
    map_add(g, "SetHomeCourse", ("GetVSpline2", "VoyageSpline"), key, ("HomeCourse", "Course"), MAP_INT_OBJ(SPLINE),
            OBJ(SPLINE), 2800, -800, key_type=INT)
    g.link(("HomeCourse", "then"), ("SetHomeCourse", "execute"))
    map_add(g, "ResetDist", ("GetVDist2", "VoyageDist"), key, None, MAP_INT_DOUBLE, DOUBLE, 3050, -800, key_type=INT)
    set_pin_default(g, "ResetDist", "Value", "0.0")
    g.link(("SetHomeCourse", "then"), ("ResetDist", "execute"))

    # phases 1 and 3: advance along the voyage spline (1: out, distance up; 3: home, distance down)
    get_self(g, "GetVSpline", "VoyageSpline", MAP_INT_OBJ(SPLINE), 0, 1600)
    get_self(g, "GetVDist", "VoyageDist", MAP_INT_DOUBLE, 0, 1700)
    SPL = f"/Script/CoreUObject.Class'{SPLINE}'"
    map_find(g, "FindSpline", ("GetVSpline", "VoyageSpline"), key, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), 1800, 100, key_type=INT)
    spline = ("FindSpline", "Value")
    map_find(g, "FindDist", ("GetVDist", "VoyageDist"), key, MAP_INT_DOUBLE, DOUBLE, 1800, 250, key_type=INT)
    g.call("Len", SPL, "GetSplineLength", 2050, 100, [("self", "in", OBJ(SPLINE), None), ("ReturnValue", "out", FLOAT, None)])
    g.link(spline, ("Len", "self"))
    g.call("StepLen", MATHLIB, "Multiply_DoubleDouble", 2050, 450,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, f'DefaultValue="{VOYAGE_TICK}"'), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetSpeed", "ShipSpeed"), ("StepLen", "A"))
    g.call("Moved", MATHLIB, "Add_DoubleDouble", 2800, 300,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("FindDist", "Value"), ("Moved", "A"))
    g.link(("StepLen", "ReturnValue"), ("Moved", "B"))

    def yaw_of(p_, dir_src, x, y):
        """The stand-in's rotation for heading dir_src."""
        g.call(p_ + "X", MATHLIB, "MakeRotFromX", x, y,
               [("X", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(ROTATOR), None)])
        g.link(dir_src, (p_ + "X", "X"))
        g.call(p_, MATHLIB, "ComposeRotators", x + 250, y,
               [("A", "in", STRUCT(ROTATOR), 'DefaultValue="0.000000,' + PROXY_YAW + ',0.000000"'),
                ("B", "in", STRUCT(ROTATOR), None), ("ReturnValue", "out", STRUCT(ROTATOR), None)])
        g.link((p_ + "X", "ReturnValue"), (p_, "B"))
        return (p_, "ReturnValue")

    def lined_up(p_, rot_a, rot_b, x, y):
        """rot_a and rot_b within 3 degrees of yaw."""
        g.call(p_ + "Delta", MATHLIB, "NormalizedDeltaRotator", x, y,
               [("A", "in", STRUCT(ROTATOR), None), ("B", "in", STRUCT(ROTATOR), None), ("ReturnValue", "out", STRUCT(ROTATOR), None)])
        g.link(rot_a, (p_ + "Delta", "A"))
        g.link(rot_b, (p_ + "Delta", "B"))
        g.call(p_ + "Break", MATHLIB, "BreakRotator", x + 250, y,
               [("InRot", "in", STRUCT(ROTATOR), None), ("Roll", "out", FLOAT, None), ("Pitch", "out", FLOAT, None),
                ("Yaw", "out", FLOAT, None)])
        g.link((p_ + "Delta", "ReturnValue"), (p_ + "Break", "InRot"))
        absyaw = dmath1(g, p_ + "Abs", "Abs", (p_ + "Break", "Yaw"), x + 500, y)
        return dmath(g, p_, "Less_DoubleDouble", absyaw, None, x + 750, y, b_default="3.0", out=BOOL)

    get_self(g, "GetEndFwds", "VoyageEndFwd", MAP_INT_VECTOR, 2050, 1100)
    map_find(g, "FindEndFwd", ("GetEndFwds", "VoyageEndFwd"), key, MAP_INT_VECTOR, STRUCT(VECTOR), 2300, 1100, key_type=INT)
    end_rot = yaw_of("EndRot", ("FindEndFwd", "Value"), 2550, 1100)
    g.call("NowRot", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_GetActorRotation", 3550, 950,
           [("self", "in", OBJ(ACTOR), None), ("ReturnValue", "out", STRUCT(ROTATOR), None)])
    g.link(proxy, ("NowRot", "self"))
    # at the start of the course: hold position until facing along it
    g.call("StartDir", SPL, "GetDirectionAtDistanceAlongSpline", 2300, 1300,
           [("self", "in", OBJ(SPLINE), None), ("Distance", "in", FLOAT, 'DefaultValue="0.0"'),
            ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(spline, ("StartDir", "self"))
    start_aligned = lined_up("StartAligned", ("NowRot", "ReturnValue"), yaw_of("StartRot", ("StartDir", "ReturnValue"), 2550, 1300), 3050, 1300)
    at_start = dmath(g, "AtStart", "Less_DoubleDouble", ("FindDist", "Value"), None, 2550, 1450, b_default="0.5", out=BOOL)
    hold = bop(g, "Hold", "BooleanAND", at_start, bnot(g, "NotAligned", start_aligned, 3800, 1350), 4050, 1400)
    g.call("Advance", MATHLIB, "SelectFloat", 3050, 450,
           [("A", "in", DOUBLE, 'DefaultValue="0.0"'), ("B", "in", DOUBLE, None), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Moved", "ReturnValue"), ("Advance", "B"))
    g.link(hold, ("Advance", "bPickA"))
    g.call("NewDist", MATHLIB, "FMin", 3300, 300,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Advance", "ReturnValue"), ("NewDist", "A"))
    g.link(("Len", "ReturnValue"), ("NewDist", "B"))
    dist = ("NewDist", "ReturnValue")
    # at the end: turn to VoyageEndFwd; arrived once facing it
    g.call("LenLess", MATHLIB, "Subtract_DoubleDouble", 3300, 450,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="0.5"'), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Len", "ReturnValue"), ("LenLess", "A"))
    at_end = dmath(g, "AtEnd", "GreaterEqual_DoubleDouble", dist, ("LenLess", "ReturnValue"), 3550, 450, out=BOOL)
    g.call("Pos", SPL, "GetLocationAtDistanceAlongSpline", 3050, 600,
           [("self", "in", OBJ(SPLINE), None), ("Distance", "in", FLOAT, None), ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(spline, ("Pos", "self"))
    g.link(dist, ("Pos", "Distance"))
    g.call("Tangent", SPL, "GetDirectionAtDistanceAlongSpline", 3050, 750,
           [("self", "in", OBJ(SPLINE), None), ("Distance", "in", FLOAT, None), ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(spline, ("Tangent", "self"))
    g.link(dist, ("Tangent", "Distance"))
    g.call("WantDir", MATHLIB, "SelectVector", 3300, 750,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("FindEndFwd", "Value"), ("WantDir", "A"))
    g.link(("Tangent", "ReturnValue"), ("WantDir", "B"))
    g.link(at_end, ("WantDir", "bPickA"))
    heading = yaw_of("Heading", ("WantDir", "ReturnValue"), 3300, 600)
    # turn toward it at no more than TurnRate degrees per second
    get_self(g, "GetTurnRate", "TurnRate", DOUBLE, 3300, 950)
    g.call("Turned", MATHLIB, "RInterpTo_Constant", 3800, 800,
           [("Current", "in", STRUCT(ROTATOR), None), ("Target", "in", STRUCT(ROTATOR), None),
            ("deltaTime", "in", FLOAT, f'DefaultValue="{VOYAGE_TICK}"'), ("InterpSpeed", "in", FLOAT, None),
            ("ReturnValue", "out", STRUCT(ROTATOR), None)])
    g.call("NowParts", MATHLIB, "BreakRotator", 3550, 1050,
           [("InRot", "in", STRUCT(ROTATOR), None), ("Roll", "out", FLOAT, None), ("Pitch", "out", FLOAT, None), ("Yaw", "out", FLOAT, None)])
    g.link(("NowRot", "ReturnValue"), ("NowParts", "InRot"))
    g.call("NowYaw", MATHLIB, "MakeRotator", 3800, 1050,
           [("Roll", "in", FLOAT, 'DefaultValue="0.0"'), ("Pitch", "in", FLOAT, 'DefaultValue="0.0"'), ("Yaw", "in", FLOAT, None),
            ("ReturnValue", "out", STRUCT(ROTATOR), None)])
    g.link(("NowParts", "Yaw"), ("NowYaw", "Yaw"))
    g.link(("NowYaw", "ReturnValue"), ("Turned", "Current"))
    g.link(heading, ("Turned", "Target"))
    g.link(("GetTurnRate", "TurnRate"), ("Turned", "InterpSpeed"))

    # stand-in and course still there?
    is_valid(g, "ProxyOk", ACTOR, 1800, 0)
    g.link(proxy, ("ProxyOk", "Object"))
    is_valid(g, "SplineOk", SPLINE, 1800, -50)
    g.link(spline, ("SplineOk", "Object"))
    both = bop(g, "BothOk", "BooleanAND", ("ProxyOk", "ReturnValue"), ("SplineOk", "ReturnValue"), 2050, 0)
    # waiting at the partner: bob in place at the course's end
    branch(g, "BrBobWait", 2050, -600)
    g.link(both, ("BrBobWait", "Condition"))
    g.link(("BrWaitDone", "else"), ("BrBobWait", "execute"))
    g.call("WaitPos", SPL, "GetLocationAtDistanceAlongSpline", 2300, -500,
           [("self", "in", OBJ(SPLINE), None), ("Distance", "in", FLOAT, None), ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(spline, ("WaitPos", "self"))
    g.link(("Len", "ReturnValue"), ("WaitPos", "Distance"))
    wait_pos, wait_rot = bob_pose(g, "Moored", key, ("WaitPos", "ReturnValue"), ("NowYaw", "ReturnValue"), 2550, -500)
    g.call("BobWait", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_SetActorLocationAndRotation", 2300, -650,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("NewLocation", "in", STRUCT(VECTOR), None), ("NewRotation", "in", STRUCT(ROTATOR), None),
            ("bSweep", "in", BOOL, 'DefaultValue="false"'), ("SweepHitResult", "out", STRUCT(HIT), None),
            ("bTeleport", "in", BOOL, 'DefaultValue="true"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("BrBobWait", "then"), ("BobWait", "execute"))
    g.link(proxy, ("BobWait", "self"))
    g.link(wait_pos, ("BobWait", "NewLocation"))
    g.link(wait_rot, ("BobWait", "NewRotation"))
    branch(g, "BrProxy", 1800, -150)
    g.link(("BrWaiting", "else"), ("BrProxy", "execute"))
    g.link(both, ("BrProxy", "Condition"))
    g.call("MoveProxy", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_SetActorLocationAndRotation", 2050, -150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("NewLocation", "in", STRUCT(VECTOR), None), ("NewRotation", "in", STRUCT(ROTATOR), None),
            ("bSweep", "in", BOOL, 'DefaultValue="false"'), ("SweepHitResult", "out", STRUCT(HIT), None),
            ("bTeleport", "in", BOOL, 'DefaultValue="true"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("BrProxy", "then"), ("MoveProxy", "execute"))
    g.link(proxy, ("MoveProxy", "self"))
    sail_pos, sail_rot = bob_pose(g, "Sailing", key, ("Pos", "ReturnValue"), ("Turned", "ReturnValue"), 4300, 600)
    g.link(sail_pos, ("MoveProxy", "NewLocation"))
    g.link(sail_rot, ("MoveProxy", "NewRotation"))
    map_add(g, "SaveDist", ("GetVDist", "VoyageDist"), key, dist, MAP_INT_DOUBLE, DOUBLE, 2300, -150, key_type=INT)
    g.link(("MoveProxy", "then"), ("SaveDist", "execute"))
    branch(g, "BrArrived", 2550, -150)
    g.link(("SaveDist", "then"), ("BrArrived", "execute"))
    end_aligned = lined_up("EndAligned", ("Turned", "ReturnValue"), end_rot, 3800, 1100)
    g.link(bop(g, "Arrived", "BooleanAND", at_end, end_aligned, 4050, 1100), ("BrArrived", "Condition"))
    user_call(g, "Arrive", "VoyageArrive", 2800, -150, ins=[("Id", INT)])
    g.link(("BrArrived", "then"), ("Arrive", "execute"))
    g.link(key, ("Arrive", "Id"))
    # stand-in or course gone (e.g. destroyed): finish the voyage so the ship is shown again
    g.link(("BrProxy", "else"), ("Arrive", "execute"))
    return g.render()


def voyage_arrive():
    """Phase 1 (at the partner): deliver the hold, shown as goods flying from the stand-in to the partner dock
    (BP_FDFling, spawned at the stand-in: Before records the partner's dock store, Launch flies what it gained),
    start the wait. Phase 3 (home): remove the stand-in, show the ship,
    end the trip. A missing stand-in also ends the trip."""
    g = Graph()
    F = "VoyageArrive"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 500)
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 0, 600)
    get_self(g, "GetVShip", "VoyageShip", MAP_INT_SHIP, 0, 700)
    get_self(g, "GetVHome", "VoyageHome", MAP_INT_VECTOR, 0, 800)
    get_self(g, "GetVTarget", "VoyageTarget", MAP_INT_VECTOR, 0, 900)
    get_self(g, "GetVPhase", "VoyagePhase", MAP_INT_INT, 0, 1000)
    get_self(g, "GetVWait", "VoyageWait", MAP_INT_DOUBLE, 0, 1100)
    get_self(g, "GetDeparted", "DepartedAt", MAP_INT_DOUBLE, 0, 1200)
    get_self(g, "GetSince", "LoadingSince", MAP_INT_DOUBLE, 0, 1300)
    get_self(g, "GetDwell", "DwellSeconds", DOUBLE, 0, 1400)
    get_local(g, "GetId", F, "Id", INT, 0, 1500)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 1600)
    get_local(g, "GetPartner", F, "Partner", OBJ(WORKDOCK), 0, 1700)
    key = ("GetId", "Id")

    map_find(g, "FindProxy", ("GetVoyages", "Voyages"), key, MAP_INT_ACTOR, OBJ(ACTOR), 0, 250, key_type=INT)
    is_valid(g, "ProxyOk", ACTOR, 250, 250)
    g.link(("FindProxy", "Value"), ("ProxyOk", "Object"))
    map_find(g, "FindPhase", ("GetVPhase", "VoyagePhase"), key, MAP_INT_INT, INT, 0, 400, key_type=INT)
    outbound = int_op(g, "Outbound", "EqualEqual_IntInt", ("FindPhase", "Value"), None, 250, 400, b_default="1")
    g.call("Deliver", MATHLIB, "BooleanAND", 500, 300,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("ProxyOk", "ReturnValue"), ("Deliver", "A"))
    g.link(outbound, ("Deliver", "B"))
    branch(g, "BrDeliver", 0, 0)
    g.link(("Deliver", "ReturnValue"), ("BrDeliver", "Condition"))

    # --- arrival at the partner: deliver, then wait
    user_call(g, "FindDock", "DockById", 250, -400, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("BrDeliver", "then"), ("FindDock", "execute"))
    g.link(key, ("FindDock", "Id"))
    set_local(g, "SetDock", F, "Dock", OBJ(WORKDOCK), 500, -400)
    g.link(("FindDock", "then"), ("SetDock", "execute"))
    g.link(("FindDock", "Dock"), ("SetDock", "Dock"))
    get_self(g, "GetVPartner", "VoyagePartner", MAP_INT_INT, 0, 1800)
    get_self(g, "GetVBerth", "VoyageBerth", MAP_INT_OBJ(NDOCK), 0, 1900)
    map_find(g, "FindPartnerId", ("GetVPartner", "VoyagePartner"), key, MAP_INT_INT, INT, 750, -550, key_type=INT)
    user_call(g, "FindPartner", "DockById", 750, -400, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("SetDock", "then"), ("FindPartner", "execute"))
    g.link(("FindPartnerId", "Value"), ("FindPartner", "Id"))
    set_local(g, "SetPartner", F, "Partner", OBJ(WORKDOCK), 1000, -400)
    g.link(("FindPartner", "then"), ("SetPartner", "execute"))
    g.link(("FindPartner", "Dock"), ("SetPartner", "Partner"))
    is_valid(g, "PartnerOk", WORKDOCK, 1250, -250)
    g.link(("GetPartner", "Partner"), ("PartnerOk", "Object"))
    branch(g, "BrPartner", 1250, -400)
    g.link(("SetPartner", "then"), ("BrPartner", "execute"))
    g.link(("PartnerOk", "ReturnValue"), ("BrPartner", "Condition"))
    fling_t = OBJ(FD_FLING_CLASS)
    fling_cls = f"/Script/Engine.BlueprintGeneratedClass'{FD_FLING_CLASS}'"
    g.call("ProxyXform", f"/Script/CoreUObject.Class'{ACTOR}'", "GetTransform", 1250, -900,
           [("self", "in", OBJ(ACTOR), None), ("ReturnValue", "out", STRUCT(TRANSFORM), None)])
    g.link(("FindProxy", "Value"), ("ProxyXform", "self"))
    fct, fcd = CLASSPIN(ACTOR, FD_FLING_CLASS)
    g.node("SpawnFling", K2 + "K2Node_SpawnActorFromClass", [], 1500, -900,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Class", "in", fct, fcd), ("ReturnValue", "out", fling_t, None),
            ("SpawnTransform", "in", STRUCT(TRANSFORM), None),
            ("CollisionHandlingOverride", "in", COLLISION_PIN, 'DefaultValue="AlwaysSpawn"'),
            ("Owner", "in", OBJ(ACTOR), None)])
    g.link(("BrPartner", "then"), ("SpawnFling", "execute"))
    g.link(("ProxyXform", "ReturnValue"), ("SpawnFling", "SpawnTransform"))
    g.call("FlingBefore", fling_cls, "Before", 1750, -900,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", fling_t, None),
            ("Partner", "in", OBJ(WORKDOCK), None)])
    g.link(("SpawnFling", "then"), ("FlingBefore", "execute"))
    g.link(("SpawnFling", "ReturnValue"), ("FlingBefore", "self"))
    g.link(("GetPartner", "Partner"), ("FlingBefore", "Partner"))
    user_call(g, "Transfer", "TransferFrom", 1500, -400,
              ins=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK))], outs=[("Total", INT)])
    g.link(("FlingBefore", "then"), ("Transfer", "execute"))
    g.call("FlingLaunch", fling_cls, "Launch", 2000, -900,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", fling_t, None),
            ("Partner", "in", OBJ(WORKDOCK), None)])
    g.link(("SpawnFling", "ReturnValue"), ("FlingLaunch", "self"))
    g.link(("GetPartner", "Partner"), ("FlingLaunch", "Partner"))
    g.link(("GetDock", "Dock"), ("Transfer", "Dock"))
    g.link(("GetPartner", "Partner"), ("Transfer", "Partner"))
    pid = dock_id_call(g, "PartnerId", ("GetPartner", "Partner"), 1500, -650)
    s = fmt_to_string(g, "FmtArrived", "Dock {d} freight arrived at partner {p}: delivered {n}",
                      [("d", INT), ("p", INT), ("n", INT)], 1750, -650)
    g.link(key, ("FmtArrived", "d"))
    g.link(pid, ("FmtArrived", "p"))
    g.link(("Transfer", "Total"), ("FmtArrived", "n"))
    log_msg(g, "LogArrived", "GetModAPI", 1750, -400)
    user_call(g, "ClearReq", "ClearRequested", 1750, -200, ins=[("Id", INT)])
    g.link(("Transfer", "then"), ("FlingLaunch", "execute"))
    g.link(("FlingLaunch", "then"), ("ClearReq", "execute"))
    g.link(key, ("ClearReq", "Id"))
    g.link(("ClearReq", "then"), ("LogArrived", "execute"))
    g.link((s, "ReturnValue"), ("LogArrived", "Msg"))
    g.call("Now", SYSLIB, "GetGameTimeInSeconds", 2250, -650, [("ReturnValue", "out", DOUBLE, None)])
    g.call("WaitEnd", MATHLIB, "Add_DoubleDouble", 2500, -650,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Now", "ReturnValue"), ("WaitEnd", "A"))
    g.link(("GetDwell", "DwellSeconds"), ("WaitEnd", "B"))
    map_add(g, "SetWait", ("GetVWait", "VoyageWait"), key, ("WaitEnd", "ReturnValue"), MAP_INT_DOUBLE, DOUBLE,
            2250, -400, key_type=INT)
    g.link(("LogArrived", "then"), ("SetWait", "execute"))
    g.link(("BrPartner", "else"), ("SetWait", "execute"))
    map_add(g, "SetWaiting", ("GetVPhase", "VoyagePhase"), key, None, MAP_INT_INT, INT, 2500, -400, key_type=INT)
    g.link(("SetWait", "then"), ("SetWaiting", "execute"))
    set_pin_default(g, "SetWaiting", "Value", "2")

    # --- back home (or stand-in lost): remove the stand-in, show the ship, end the trip
    branch(g, "BrHasProxy", 250, 300)
    g.link(("BrDeliver", "else"), ("BrHasProxy", "execute"))
    g.link(("ProxyOk", "ReturnValue"), ("BrHasProxy", "Condition"))
    g.call("Destroy", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_DestroyActor", 500, 300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None)])
    g.link(("BrHasProxy", "then"), ("Destroy", "execute"))
    g.link(("FindProxy", "Value"), ("Destroy", "self"))
    map_find(g, "FindShip", ("GetVShip", "VoyageShip"), key, MAP_INT_SHIP, OBJ(SHIP), 500, 600, key_type=INT)
    is_valid(g, "ShipOk", SHIP, 750, 600)
    g.link(("FindShip", "Value"), ("ShipOk", "Object"))
    branch(g, "BrShip", 750, 300)
    g.link(("Destroy", "then"), ("BrShip", "execute"))
    g.link(("BrHasProxy", "else"), ("BrShip", "execute"))
    g.link(("ShipOk", "ReturnValue"), ("BrShip", "Condition"))
    _, child = zoomed_child(g, "Z", ("FindShip", "Value"), 1000, 600)
    set_hidden(g, "ShowShip", ("FindShip", "Value"), False, 1000, 300)
    g.link(("BrShip", "then"), ("ShowShip", "execute"))
    set_hidden(g, "ShowChild", child, False, 1250, 300)
    g.link(("ShowShip", "then"), ("ShowChild", "execute"))

    prev_list = [("ShowChild", "then"), ("BrShip", "else")]
    for i, (name, mp, mtype) in enumerate((
            ("RemVoyage", ("GetVoyages", "Voyages"), MAP_INT_ACTOR),
            ("RemShip", ("GetVShip", "VoyageShip"), MAP_INT_SHIP),
            ("RemHome", ("GetVHome", "VoyageHome"), MAP_INT_VECTOR),
            ("RemTarget", ("GetVTarget", "VoyageTarget"), MAP_INT_VECTOR),
            ("RemPhase", ("GetVPhase", "VoyagePhase"), MAP_INT_INT),
            ("RemWait", ("GetVWait", "VoyageWait"), MAP_INT_DOUBLE),
            ("RemDeparted", ("GetDeparted", "DepartedAt"), MAP_INT_DOUBLE),
            ("RemSince", ("GetSince", "LoadingSince"), MAP_INT_DOUBLE),
            ("RemBerth", ("GetVBerth", "VoyageBerth"), MAP_INT_OBJ(NDOCK)),
            ("RemPartner", ("GetVPartner", "VoyagePartner"), MAP_INT_INT))):
        map_remove(g, name, mp, key, mtype, 1500 + 250 * i, 300)
        for prev in prev_list:
            g.link(prev, (name, "execute"))
        prev_list = [(name, "then")]
    s2 = fmt_to_string(g, "FmtHome", "Dock {d}: ship back home", [("d", INT)], 3500, 500)
    g.link(key, ("FmtHome", "d"))
    log_msg(g, "LogHome", "GetModAPI", 3500, 300)
    g.link(prev_list[0], ("LogHome", "execute"))
    g.link((s2, "ReturnValue"), ("LogHome", "Msg"))
    return g.render()


SPECS = {
    "VoyageTick": fn_spec(("BrNone", "execute"), locals_=[("Id", INT), ("Proxy", OBJ(ACTOR)), ("Phase", INT)]),
    "StartVoyage": fn_spec(("SetId", "execute"), inputs=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP))],
                           locals_=[("Id", INT), ("Proxy", OBJ(ACTOR)), ("Target", OBJ(NDOCK))]),
    "VoyageArrive": fn_spec(("BrDeliver", "execute"), inputs=[("Id", INT)],
                            locals_=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK))]),
}


GRAPHS = {
    "StartVoyage": start_voyage,
    "VoyageTick": voyage_tick,
    "VoyageArrive": voyage_arrive,
}
