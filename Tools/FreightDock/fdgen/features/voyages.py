"""Voyages: StartVoyage spawns the stand-in and course, VoyageTick moves it along the spline (moored / sailing /
waiting phases), VoyageArrive unloads (with goods flying to the dock, BP_FDFling) and returns the ship.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import (
    BOOL, CLASSPIN, COLLISION_PIN, DOUBLE, EXEC, FLOAT, INT, INT_ARRAY_T, MAP_INT_ACTOR,
    MAP_INT_DOUBLE, MAP_INT_INT, MAP_INT_OBJ, MAP_INT_SHIP, MAP_INT_VECTOR, OBJ, SPLINE_SPACE, STRUCT)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, CHILDCOMP, FD_FLING_CLASS, HIT, K2, MAPLIB, MATHLIB, MODAPI, NDOCK, NDOCKSTATE,
    ROTATOR, SHIP, SHIPSTATE, SPLINE, SYSLIB, TRANSFORM, VECTOR, VOYAGE_LIB, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, bnot, bop, branch, break_struct, clear_timer, dmath, dmath1, for_each,
    get_local, get_member, get_self, int_op, is_valid, loom_call, map_add, map_find, map_remove, set_local,
    set_pin_default, start_timer, user_call)
from fdgen.core.text import fmt_to_string, log_msg
from fdgen.features.docks import dock_id_call
from fdgen.features.standins import PROXY_YAW, bob_pose, set_hidden, zoomed_child


VOYAGE_TICK = "0.016000"    # ~60 steps per second (game time)


def start_voyage():
    """Spawn a stand-in from Ship's zoomed-in model, hide the real ship, and sail the stand-in to Target's berth."""
    g = Graph()
    F = "StartVoyage"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 500)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 600)
    get_local(g, "GetTarget", F, "Target", OBJ(WORKDOCK), 0, 700)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 800)
    get_local(g, "GetId", F, "Id", INT, 0, 900)
    get_local(g, "GetProxy", F, "Proxy", OBJ(ACTOR), 0, 1000)
    get_local(g, "GetBerthTo", F, "BerthTo", OBJ(NDOCK), 0, 1100)
    ship = ("GetShip", "Ship")
    key = ("GetId", "Id")

    set_local(g, "SetId", F, "Id", INT, 0, 0)
    g.link(dock_id_call(g, "DockId", ("GetDock", "Dock"), 0, 250), ("SetId", "Id"))
    user_call(g, "FindBerthTo", "NauticalDockAt", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Best", OBJ(NDOCK))])
    g.link(("SetId", "then"), ("FindBerthTo", "execute"))
    g.link(("GetTarget", "Target"), ("FindBerthTo", "Dock"))
    set_local(g, "SetBerthTo", F, "BerthTo", OBJ(NDOCK), 500, 0)
    g.link(("FindBerthTo", "then"), ("SetBerthTo", "execute"))
    g.link(("FindBerthTo", "Best"), ("SetBerthTo", "BerthTo"))

    zoomed, child = zoomed_child(g, "Z", ship, 500, 300)
    is_valid(g, "ChildOk", ACTOR, 750, 400)
    g.link(child, ("ChildOk", "Object"))
    is_valid(g, "BerthToOk", NDOCK, 750, 500)
    g.link(("GetBerthTo", "BerthTo"), ("BerthToOk", "Object"))
    g.call("BothOk", MATHLIB, "BooleanAND", 1000, 450,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("ChildOk", "ReturnValue"), ("BothOk", "A"))
    g.link(("BerthToOk", "ReturnValue"), ("BothOk", "B"))
    branch(g, "BrOk", 750, 0)
    g.link(("SetBerthTo", "then"), ("BrOk", "execute"))
    g.link(("BothOk", "ReturnValue"), ("BrOk", "Condition"))
    log_msg(g, "LogFail", "GetModAPI", 1000, 150,
            literal="StartVoyage: no ship model or target berth - falling back to the timed trip")
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
    get_member(g, "BerthToState", NDOCK, "State", STRUCT(NDOCKSTATE), 1750, 300)
    g.link(("GetBerthTo", "BerthTo"), ("BerthToState", "self"))
    break_struct(g, "BreakBerthTo", NDOCKSTATE,
                 [("berthLocation", STRUCT(VECTOR)), ("berthOutDirection", STRUCT(VECTOR))], 2000, 300)
    get_self(g, "GetStandOff", "StandOff", DOUBLE, 2000, 450)
    g.call("OutStep", MATHLIB, "Multiply_VectorFloat", 2250, 450,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("BreakBerthTo", "berthOutDirection"), ("OutStep", "A"))
    g.link(("GetStandOff", "StandOff"), ("OutStep", "B"))
    g.call("StandPos", MATHLIB, "Add_VectorVector", 2500, 450,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("BreakBerthTo", "berthLocation"), ("StandPos", "A"))
    g.link(("OutStep", "ReturnValue"), ("StandPos", "B"))
    g.link(("BerthToState", "State"), ("BreakBerthTo", "NauticalDockState"))
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
    get_self(g, "GetVTargetId", "VoyageTargetId", MAP_INT_INT, 2000, -900)
    map_add(g, "AddTargetId", ("GetVTargetId", "VoyageTargetId"), key, dock_id_call(g, "TargetId", ("GetTarget", "Target"), 3750, 450),
            MAP_INT_INT, INT, 3750, 0, key_type=INT)
    g.link(("AddBerth", "then"), ("AddTargetId", "execute"))
    # the course: MakeCourse builds the outbound spline (any previous one for this dock is dropped first)
    X = 4000
    get_self(g, "GetVSpline", "VoyageSpline", MAP_INT_OBJ(SPLINE), 2000, -1000)
    get_self(g, "GetVDist", "VoyageDist", MAP_INT_DOUBLE, 2000, -1100)
    map_find(g, "OldSpline", ("GetVSpline", "VoyageSpline"), key, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), X, 300, key_type=INT)
    is_valid(g, "OldOk", SPLINE, X + 250, 300)
    g.link(("OldSpline", "Value"), ("OldOk", "Object"))
    branch(g, "BrOld", X, 0)
    g.link(("AddTargetId", "then"), ("BrOld", "execute"))
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
    """VoyageTick (the voyage timer, every VOYAGE_TICK of game time): BPL_FDVoyage.VoyageTick - moves every stand-in,
    waits at the target, turns for home and hands arrivals to VoyageArrive (see there)."""
    g = Graph()
    loom_call(g, "Call", VOYAGE_LIB, "VoyageTick", 0, 0)
    return g.render()


def voyage_arrive():
    """Phase 1 (at the target): deliver the hold, shown as goods flying from the stand-in to the target dock
    (BP_FDFling, spawned at the stand-in: Before records the target's dock store, Launch flies what it gained),
    start the wait. Phase 3 (home): remove the stand-in, show the ship,
    end the trip. A missing stand-in also ends the trip."""
    g = Graph()
    F = "VoyageArrive"
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
    get_local(g, "GetTarget", F, "Target", OBJ(WORKDOCK), 0, 1700)
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

    # --- arrival at the target: deliver, then wait
    user_call(g, "FindDock", "DockById", 250, -400, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("BrDeliver", "then"), ("FindDock", "execute"))
    g.link(key, ("FindDock", "Id"))
    set_local(g, "SetDock", F, "Dock", OBJ(WORKDOCK), 500, -400)
    g.link(("FindDock", "then"), ("SetDock", "execute"))
    g.link(("FindDock", "Dock"), ("SetDock", "Dock"))
    get_self(g, "GetVTargetId", "VoyageTargetId", MAP_INT_INT, 0, 1800)
    get_self(g, "GetVBerth", "VoyageBerth", MAP_INT_OBJ(NDOCK), 0, 1900)
    map_find(g, "FindTargetId", ("GetVTargetId", "VoyageTargetId"), key, MAP_INT_INT, INT, 750, -550, key_type=INT)
    user_call(g, "FindTarget", "DockById", 750, -400, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("SetDock", "then"), ("FindTarget", "execute"))
    g.link(("FindTargetId", "Value"), ("FindTarget", "Id"))
    set_local(g, "SetTarget", F, "Target", OBJ(WORKDOCK), 1000, -400)
    g.link(("FindTarget", "then"), ("SetTarget", "execute"))
    g.link(("FindTarget", "Dock"), ("SetTarget", "Target"))
    is_valid(g, "TargetOk", WORKDOCK, 1250, -250)
    g.link(("GetTarget", "Target"), ("TargetOk", "Object"))
    branch(g, "BrTarget", 1250, -400)
    g.link(("SetTarget", "then"), ("BrTarget", "execute"))
    g.link(("TargetOk", "ReturnValue"), ("BrTarget", "Condition"))
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
    g.link(("BrTarget", "then"), ("SpawnFling", "execute"))
    g.link(("ProxyXform", "ReturnValue"), ("SpawnFling", "SpawnTransform"))
    g.call("FlingBefore", fling_cls, "Before", 1750, -900,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", fling_t, None),
            ("Target", "in", OBJ(WORKDOCK), None)])
    g.link(("SpawnFling", "then"), ("FlingBefore", "execute"))
    g.link(("SpawnFling", "ReturnValue"), ("FlingBefore", "self"))
    g.link(("GetTarget", "Target"), ("FlingBefore", "Target"))
    user_call(g, "Transfer", "TransferFrom", 1500, -400,
              ins=[("Dock", OBJ(WORKDOCK)), ("Target", OBJ(WORKDOCK))], outs=[("Total", INT)])
    g.link(("FlingBefore", "then"), ("Transfer", "execute"))
    g.call("FlingLaunch", fling_cls, "Launch", 2000, -900,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", fling_t, None),
            ("Target", "in", OBJ(WORKDOCK), None)])
    g.link(("SpawnFling", "ReturnValue"), ("FlingLaunch", "self"))
    g.link(("GetTarget", "Target"), ("FlingLaunch", "Target"))
    g.link(("GetDock", "Dock"), ("Transfer", "Dock"))
    g.link(("GetTarget", "Target"), ("Transfer", "Target"))
    user_call(g, "ClearReq", "ClearRequested", 1750, -200, ins=[("Id", INT)])
    g.link(("Transfer", "then"), ("FlingLaunch", "execute"))
    g.link(("FlingLaunch", "then"), ("ClearReq", "execute"))
    g.link(key, ("ClearReq", "Id"))
    g.call("Now", SYSLIB, "GetGameTimeInSeconds", 2250, -650, [("ReturnValue", "out", DOUBLE, None)])
    g.call("WaitEnd", MATHLIB, "Add_DoubleDouble", 2500, -650,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Now", "ReturnValue"), ("WaitEnd", "A"))
    g.link(("GetDwell", "DwellSeconds"), ("WaitEnd", "B"))
    map_add(g, "SetWait", ("GetVWait", "VoyageWait"), key, ("WaitEnd", "ReturnValue"), MAP_INT_DOUBLE, DOUBLE,
            2250, -400, key_type=INT)
    g.link(("ClearReq", "then"), ("SetWait", "execute"))
    g.link(("BrTarget", "else"), ("SetWait", "execute"))
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
            ("RemTargetId", ("GetVTargetId", "VoyageTargetId"), MAP_INT_INT))):
        map_remove(g, name, mp, key, mtype, 1500 + 250 * i, 300)
        for prev in prev_list:
            g.link(prev, (name, "execute"))
        prev_list = [(name, "then")]
    return g.render()


SPECS = {
    "VoyageTick": fn_spec(("Call", "execute")),
    "StartVoyage": fn_spec(("SetId", "execute"), inputs=[("Dock", OBJ(WORKDOCK)), ("Target", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP))],
                           locals_=[("Id", INT), ("Proxy", OBJ(ACTOR)), ("BerthTo", OBJ(NDOCK))]),
    "VoyageArrive": fn_spec(("BrDeliver", "execute"), inputs=[("Id", INT)],
                            locals_=[("Dock", OBJ(WORKDOCK)), ("Target", OBJ(WORKDOCK))]),
}


GRAPHS = {
    "StartVoyage": start_voyage,
    "VoyageTick": voyage_tick,
    "VoyageArrive": voyage_arrive,
}
