"""Voyages: StartVoyage spawns the stand-in and course, VoyageTick moves it along the spline (moored / sailing /
waiting phases), BPL_FDVoyage.VoyageArrive unloads (with goods flying to the dock, BP_FDFling) and returns the ship.
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


def spawn_fling():
    """SpawnFling(At) -> Fling: a BP_FDFling at At (for BPL_FDVoyage.VoyageArrive: Loom can't spawn actors)."""
    g = Graph()
    get_local(g, "GetAt", "SpawnFling", "At", STRUCT(TRANSFORM), 0, 250)
    fct, fcd = CLASSPIN(ACTOR, FD_FLING_CLASS)
    g.node("Spawn", K2 + "K2Node_SpawnActorFromClass", [], 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Class", "in", fct, fcd), ("ReturnValue", "out", OBJ(FD_FLING_CLASS), None),
            ("SpawnTransform", "in", STRUCT(TRANSFORM), None),
            ("CollisionHandlingOverride", "in", COLLISION_PIN, 'DefaultValue="AlwaysSpawn"'),
            ("Owner", "in", OBJ(ACTOR), None)])
    g.link(("GetAt", "At"), ("Spawn", "SpawnTransform"))
    return g.render()


SPECS = {
    "VoyageTick": fn_spec(("Call", "execute")),
    "StartVoyage": fn_spec(("SetId", "execute"), inputs=[("Dock", OBJ(WORKDOCK)), ("Target", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP))],
                           locals_=[("Id", INT), ("Proxy", OBJ(ACTOR)), ("BerthTo", OBJ(NDOCK))]),
    "SpawnFling": fn_spec(("Spawn", "execute"), inputs=[("At", STRUCT(TRANSFORM))], outputs=[("Fling", OBJ(FD_FLING_CLASS))],
                          returns=[("Spawn", "then")], values=[("Spawn", "ReturnValue", "Fling")]),
}


GRAPHS = {
    "StartVoyage": start_voyage,
    "VoyageTick": voyage_tick,
    "SpawnFling": spawn_fling,
}
