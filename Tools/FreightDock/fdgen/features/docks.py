"""Freight dock lookup: is a work dock a freight dock, dock <-> building ID, the Docks list, the dock under the
cursor, the ship moored at a dock, and the nautical dock at a position.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import BOOL, EXEC, INT, NAME, OBJ, STR, STRUCT
from fdgen.core.paths import (
    ACTOR, ARRAYLIB, CURSORCAST, FREIGHT_DOCK_CLASS, GRIDACTOR, K2, MATHLIB, NDOCK,
    NDOCKSTATE, NET_LIB, PLAYERSTATE, SELECTTOOL, SHIP, STATICS, STRLIB, VECTOR, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    all_actors, branch, break_struct, clear_var, comp_owner, find_component,
    for_each, get_local, get_member, get_self, int_op, is_valid, loom_call, set_local, user_call)


def dock_id_call(g, name, dock_src, x, y):
    g.node(name, K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="DockIdOf",bSelfContext=True)'], x, y,
           [("Dock", "in", OBJ(WORKDOCK), None), ("Id", "out", INT, None)])
    g.link(dock_src, (name, "Dock"))
    return (name, "Id")


def is_freight_call(g, name, dock_src, x, y):
    user_call(g, name, "IsFreightDock", x, y, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Result", BOOL)], impure=False)
    g.link(dock_src, (name, "Dock"))
    return (name, "Result")


def is_freight_dock():
    """Pure IsFreightDock(Dock) -> Result: the dock's building is a navaldock_freight."""
    g = Graph()
    get_local(g, "GetDock", "IsFreightDock", "Dock", OBJ(WORKDOCK), 0, 0)
    comp_owner(g, "Owner", WORKDOCK, 250, 0)
    g.link(("GetDock", "Dock"), ("Owner", "self"))
    g.call("OwnerClass", STATICS, "GetObjectClass", 500, 0,
           [("Object", "in", OBJ("/Script/CoreUObject.Object"), None),
            ("ReturnValue", "out", ['PinType.PinCategory="class"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Class'/Script/CoreUObject.Object'\""], None)])
    g.link(("Owner", "ReturnValue"), ("OwnerClass", "Object"))
    classpin = ['PinType.PinCategory="class"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Class'/Script/CoreUObject.Object'\""]
    g.call("IsChild", MATHLIB, "ClassIsChildOf", 750, 0,
           [("TestClass", "in", classpin, None),
            ("ParentClass", "in", classpin, f"DefaultObject=\"/Script/Engine.BlueprintGeneratedClass'{FREIGHT_DOCK_CLASS}'\""),
            ("ReturnValue", "out", BOOL, None)])
    g.link(("OwnerClass", "ReturnValue"), ("IsChild", "TestClass"))
    return g.render()


def dock_id_of():
    g = Graph()
    comp_owner(g, "Owner", WORKDOCK, 0, 0)
    get_local(g, "GetDock", "DockIdOf", "Dock", OBJ(WORKDOCK), -250, 0)
    g.link(("GetDock", "Dock"), ("Owner", "self"))
    g.node("CastGrid", K2 + "K2Node_DynamicCast",
           [f"TargetType=\"/Script/CoreUObject.Class'{GRIDACTOR}'\"", "PureState=Pure"], 250, 0,
           [("Object", "in", OBJ(ACTOR), None), ("AsGrid Actor", "out", OBJ(GRIDACTOR), None),
            ("bSuccess", "out", BOOL, None)])
    g.link(("Owner", "ReturnValue"), ("CastGrid", "Object"))
    get_member(g, "GetId", GRIDACTOR, "ID", INT, 500, 0)
    g.link(("CastGrid", "AsGrid Actor"), ("GetId", "self"))
    return g.render()


def dock_by_id():
    g = Graph()
    F = "DockById"
    g.node("ClearFound", K2 + "K2Node_VariableSet", [local_var(F, "Found")], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Found", "in", OBJ(WORKDOCK), None), ("Output_Get", "out", OBJ(WORKDOCK), None)])
    all_actors(g, "GetAll", ACTOR, 250, 0)
    g.link(("ClearFound", "then"), ("GetAll", "execute"))
    for_each(g, "ForActors", OBJ(ACTOR), 550, 0)
    g.link(("GetAll", "then"), ("ForActors", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForActors", "Array"))
    comp = find_component(g, "Comp", ("ForActors", "Array Element"), WORKDOCK, 550, 250)
    is_valid(g, "CompValid", WORKDOCK, 800, 250)
    g.link(comp, ("CompValid", "Object"))
    branch(g, "BrIsDock", 850, 0)
    g.link(("ForActors", "LoopBody"), ("BrIsDock", "execute"))
    g.link(("CompValid", "ReturnValue"), ("BrIsDock", "Condition"))
    idp = dock_id_call(g, "CompId", comp, 1050, 250)
    get_local(g, "GetId", F, "Id", INT, 1050, 400)
    g.call("IdMatch", MATHLIB, "EqualEqual_IntInt", 1300, 250,
           [("A", "in", INT, None), ("B", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(idp, ("IdMatch", "A"))
    g.link(("GetId", "Id"), ("IdMatch", "B"))
    branch(g, "BrMatch", 1100, 0)
    g.link(("BrIsDock", "then"), ("BrMatch", "execute"))
    g.link(("IdMatch", "ReturnValue"), ("BrMatch", "Condition"))
    set_local(g, "SetFound", F, "Found", OBJ(WORKDOCK), 1350, 0)
    g.link(("BrMatch", "then"), ("SetFound", "execute"))
    g.link(comp, ("SetFound", "Found"))
    get_local(g, "GetFoundForReturn", F, "Found", OBJ(WORKDOCK), 550, -200)
    return g.render()


def find_selected_dock():
    """Replacement body for FindDockUnderCursor: the dock the player has selected, plus the game's cursor position."""
    g = Graph()
    F = "FindDockUnderCursor"
    all_actors(g, "GetTools", SELECTTOOL, 0, 0)
    for_each(g, "ForTools", OBJ(SELECTTOOL), 300, 0)
    g.link(("GetTools", "then"), ("ForTools", "Exec"))
    g.link(("GetTools", "OutActors"), ("ForTools", "Array"))
    set_local(g, "SetSel", F, "Sel", OBJ(SELECTTOOL), 600, 0)
    g.link(("ForTools", "LoopBody"), ("SetSel", "execute"))
    g.link(("ForTools", "Array Element"), ("SetSel", "Sel"))

    g.call("GetPS", STATICS, "GetPlayerState", 300, 300,
           [("PlayerStateIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ("/Script/Engine.PlayerState"), None)])
    g.node("CastPS", K2 + "K2Node_DynamicCast",
           [f"TargetType=\"/Script/CoreUObject.Class'{PLAYERSTATE}'\"", "PureState=Pure"], 550, 300,
           [("Object", "in", OBJ("/Script/Engine.PlayerState"), None),
            ("AsArco Player State", "out", OBJ(PLAYERSTATE), None), ("bSuccess", "out", BOOL, None)])
    g.link(("GetPS", "ReturnValue"), ("CastPS", "Object"))
    get_member(g, "CursorInfo", PLAYERSTATE, "m_cursorCastInfo", STRUCT(CURSORCAST), 800, 300)
    g.link(("CastPS", "AsArco Player State"), ("CursorInfo", "self"))
    break_struct(g, "BreakCursor", CURSORCAST, [("worldPos_atZLevel", STRUCT(VECTOR))], 1050, 300)
    g.link(("CursorInfo", "m_cursorCastInfo"), ("BreakCursor", "CursorCastInfo"))
    set_local(g, "SetLoc", F, "Loc", STRUCT(VECTOR), 600, -200)
    g.link(("ForTools", "Completed"), ("SetLoc", "execute"))
    g.link(("BreakCursor", "worldPos_atZLevel"), ("SetLoc", "Loc"))

    get_local(g, "GetSel", F, "Sel", OBJ(SELECTTOOL), 850, -450)
    get_member(g, "Selected", SELECTTOOL, "m_currentlySelectedGridActor", OBJ(GRIDACTOR), 1100, -450)
    g.link(("GetSel", "Sel"), ("Selected", "self"))
    find_component(g, "SelectedDock", ("Selected", "m_currentlySelectedGridActor"), WORKDOCK, 1350, -450)
    get_local(g, "GetLocForReturn", F, "Loc", STRUCT(VECTOR), 1350, -300)
    return g.render()


def refresh_docks():
    """Rebuild the member Docks array from every actor with a WorkDock."""
    g = Graph()
    get_self(g, "GetDocksToClear", "Docks", OBJ(WORKDOCK, "Array"), 0, 200)
    g.node("ClearDocks", K2 + "K2Node_CallArrayFunction",
           [f'FunctionReference=(MemberParent="{ARRAYLIB}",MemberName="Array_Clear")'], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetArray", "in", OBJ(WORKDOCK, "Array"), None)])
    g.link(("GetDocksToClear", "Docks"), ("ClearDocks", "TargetArray"))
    all_actors(g, "GetAll", ACTOR, 250, 0)
    g.link(("ClearDocks", "then"), ("GetAll", "execute"))
    for_each(g, "ForActors", OBJ(ACTOR), 550, 0)
    g.link(("GetAll", "then"), ("ForActors", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForActors", "Array"))
    comp = find_component(g, "Comp", ("ForActors", "Array Element"), WORKDOCK, 550, 250)
    is_valid(g, "CompValid", WORKDOCK, 800, 250)
    g.link(comp, ("CompValid", "Object"))
    branch(g, "BrDock", 850, 0)
    g.link(("ForActors", "LoopBody"), ("BrDock", "execute"))
    g.link(("CompValid", "ReturnValue"), ("BrDock", "Condition"))
    branch(g, "BrFreight", 1100, 0)
    g.link(("BrDock", "then"), ("BrFreight", "execute"))
    g.link(is_freight_call(g, "IsFreight", comp, 1100, 250), ("BrFreight", "Condition"))
    get_self(g, "GetDocks", "Docks", OBJ(WORKDOCK, "Array"), 1100, 400)
    g.node("AddDock", K2 + "K2Node_CallArrayFunction",
           [f'FunctionReference=(MemberParent="{ARRAYLIB}",MemberName="Array_Add")'], 1350, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetArray", "in", OBJ(WORKDOCK, "Array"), None), ("NewItem", "in", OBJ(WORKDOCK), None),
            ("ReturnValue", "out", INT, None)])
    g.link(("BrFreight", "then"), ("AddDock", "execute"))
    g.link(("GetDocks", "Docks"), ("AddDock", "TargetArray"))
    g.link(comp, ("AddDock", "NewItem"))
    return g.render()


def building_by_id():
    g = Graph()
    F = "BuildingById"
    clear_var(g, "ClearFound", [local_var(F, "Found")], "Found", OBJ(GRIDACTOR), 0, 0)
    all_actors(g, "GetAll", GRIDACTOR, 250, 0)
    g.link(("ClearFound", "then"), ("GetAll", "execute"))
    for_each(g, "ForBuildings", OBJ(GRIDACTOR), 550, 0)
    g.link(("GetAll", "then"), ("ForBuildings", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForBuildings", "Array"))
    get_member(g, "BuildingId", GRIDACTOR, "ID", INT, 550, 250)
    g.link(("ForBuildings", "Array Element"), ("BuildingId", "self"))
    get_local(g, "GetId", F, "Id", INT, 550, 400)
    match = int_op(g, "IdMatch", "EqualEqual_IntInt", ("BuildingId", "ID"), ("GetId", "Id"), 800, 250)
    branch(g, "BrMatch", 850, 0)
    g.link(("ForBuildings", "LoopBody"), ("BrMatch", "execute"))
    g.link(match, ("BrMatch", "Condition"))
    set_local(g, "SetFound", F, "Found", OBJ(GRIDACTOR), 1100, 0)
    g.link(("BrMatch", "then"), ("SetFound", "execute"))
    g.link(("ForBuildings", "Array Element"), ("SetFound", "Found"))
    get_local(g, "GetFoundForReturn", F, "Found", OBJ(GRIDACTOR), 550, -200)
    return g.render()


def ship_at_dock():
    """ShipAtDock(Dock) -> Ship: BPL_FDNet.ShipAtDock - the ship whose docked berth is the dock's own."""
    g = Graph()
    get_local(g, "GetDock", "ShipAtDock", "Dock", OBJ(WORKDOCK), 0, 250)
    loom_call(g, "Call", NET_LIB, "ShipAtDock", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("ReturnValue", OBJ(SHIP))])
    g.link(("GetDock", "Dock"), ("Call", "Dock"))
    return g.render()


def nautical_dock_at():
    """The nautical dock whose externalName is playerDock_<the work dock's building ID>."""
    g = Graph()
    F = "NauticalDockAt"
    clear_var(g, "ClearBest", [local_var(F, "BestND")], "BestND", OBJ(NDOCK), 0, 0)
    all_actors(g, "GetAll", NDOCK, 250, 0)
    g.link(("ClearBest", "then"), ("GetAll", "execute"))
    for_each(g, "ForEach", OBJ(NDOCK), 550, 0)
    g.link(("GetAll", "then"), ("ForEach", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForEach", "Array"))

    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 450)
    dock_id = dock_id_call(g, "DockId", ("GetDock", "Dock"), 250, 450)
    g.call("IdStr", STRLIB, "Conv_IntToString", 500, 450,
           [("InInt", "in", INT, None), ("ReturnValue", "out", STR, None)])
    g.link(dock_id, ("IdStr", "InInt"))
    g.call("ExtStr", STRLIB, "Concat_StrStr", 750, 450,
           [("A", "in", STR, 'DefaultValue="playerDock_"'), ("B", "in", STR, None), ("ReturnValue", "out", STR, None)])
    g.link(("IdStr", "ReturnValue"), ("ExtStr", "B"))
    g.call("ExtName", STRLIB, "Conv_StringToName", 1000, 450,
           [("InString", "in", STR, None), ("ReturnValue", "out", NAME, None)])
    g.link(("ExtStr", "ReturnValue"), ("ExtName", "InString"))

    get_member(g, "GetState", NDOCK, "State", STRUCT(NDOCKSTATE), 550, 250)
    g.link(("ForEach", "Array Element"), ("GetState", "self"))
    break_struct(g, "BreakState", NDOCKSTATE, [("externalName", NAME)], 800, 250)
    g.link(("GetState", "State"), ("BreakState", "NauticalDockState"))
    g.call("Match", MATHLIB, "EqualEqual_NameName", 1250, 250,
           [("A", "in", NAME, None), ("B", "in", NAME, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("BreakState", "externalName"), ("Match", "A"))
    g.link(("ExtName", "ReturnValue"), ("Match", "B"))
    branch(g, "BrMatch", 1250, 0)
    g.link(("ForEach", "LoopBody"), ("BrMatch", "execute"))
    g.link(("Match", "ReturnValue"), ("BrMatch", "Condition"))
    set_local(g, "SetBest", F, "BestND", OBJ(NDOCK), 1500, 0)
    g.link(("BrMatch", "then"), ("SetBest", "execute"))
    g.link(("ForEach", "Array Element"), ("SetBest", "BestND"))
    get_local(g, "GetBestForReturn", F, "BestND", OBJ(NDOCK), 550, -200)
    return g.render()


SPECS = {
    "ShipAtDock": fn_spec(("Call", "execute"), inputs=[("Dock", OBJ(WORKDOCK))], outputs=[("Ship", OBJ(SHIP))],
                          returns=[("Call", "then")], values=[("Call", "ReturnValue", "Ship")]),
}


GRAPHS = {
    "DockIdOf": dock_id_of,
    "DockById": dock_by_id,
    "FindDockUnderCursor": find_selected_dock,
    "RefreshDocks": refresh_docks,
    "BuildingById": building_by_id,
    "ShipAtDock": ship_at_dock,
    "NauticalDockAt": nautical_dock_at,
    "IsFreightDock": is_freight_dock,
}
