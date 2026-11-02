"""Stand-in ships: the real ship is hidden (and its collision disabled) while a stand-in model sails the route.
Bobbing pose, and clicking a stand-in (StandInClick) to select it.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import BOOL, DOUBLE, EXEC, FLOAT, INT, INT_ARRAY_T, KEY, MAP_INT_ACTOR, OBJ, STRUCT
from fdgen.core.paths import (
    ACTOR, CHILDCOMP, GRIDACTOR, K2, MAPLIB, MATHLIB, PC, PLAYPAWN, ROTATOR, SHIP, STATICS,
    SYSLIB, VECTOR, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, bnot, bop, branch, break_vec, clear_var, comp_owner, dmath, dmath1, for_each,
    get_local, get_member, get_self, is_valid, make_vec, map_find, set_local, set_member, user_call)


def stand_in_click():
    """StandInClick (every tick, from PairKeyTick): a left click within HoverRadius of a stand-in pans the camera to
    its home dock (the play pawn eases toward its desired pan position). It doesn't select the dock: writing the
    game's selection doesn't open the dock's panel, and would make the player click elsewhere before selecting it.
    Locals: Cursor (Vector), Picked (Grid Actor)."""
    g = Graph()
    F = "StandInClick"
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 0, 600)
    get_self(g, "GetHover", "HoverRadius", DOUBLE, 0, 700)
    get_local(g, "GetCursor", F, "Cursor", STRUCT(VECTOR), 0, 800)
    get_local(g, "GetPicked", F, "Picked", OBJ(GRIDACTOR), 0, 900)

    # a click: where on the sea plane
    g.call("PC", STATICS, "GetPlayerController", 1000, 300,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ(PC), None)])
    g.call("Clicked", f"/Script/CoreUObject.Class'{PC}'", "WasInputKeyJustPressed", 1250, 300,
           [("self", "in", OBJ(PC), None), ("Key", "in", KEY, 'DefaultValue="LeftMouseButton"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("PC", "ReturnValue"), ("Clicked", "self"))
    branch(g, "BrClicked", 1250, 0)
    g.link(("Clicked", "ReturnValue"), ("BrClicked", "Condition"))
    g.call("Deproject", f"/Script/CoreUObject.Class'{PC}'", "DeprojectMousePositionToWorld", 1250, 450,
           [("self", "in", OBJ(PC), None), ("WorldLocation", "out", STRUCT(VECTOR), None),
            ("WorldDirection", "out", STRUCT(VECTOR), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("PC", "ReturnValue"), ("Deproject", "self"))
    g.call("RayLen", MATHLIB, "Multiply_VectorFloat", 1500, 550,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", DOUBLE, 'DefaultValue="10000000.0"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("Deproject", "WorldDirection"), ("RayLen", "A"))
    g.call("RayEnd", MATHLIB, "Add_VectorVector", 1750, 550,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("Deproject", "WorldLocation"), ("RayEnd", "A"))
    g.link(("RayLen", "ReturnValue"), ("RayEnd", "B"))
    g.call("SeaHit", MATHLIB, "LinePlaneIntersection_OriginNormal", 2000, 450,
           [("LineStart", "in", STRUCT(VECTOR), None), ("LineEnd", "in", STRUCT(VECTOR), None),
            ("PlaneOrigin", "in", STRUCT(VECTOR), 'DefaultValue="0.000000,0.000000,0.000000"'),
            ("PlaneNormal", "in", STRUCT(VECTOR), 'DefaultValue="0.000000,0.000000,1.000000"'),
            ("T", "out", FLOAT, None), ("Intersection", "out", STRUCT(VECTOR), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Deproject", "WorldLocation"), ("SeaHit", "LineStart"))
    g.link(("RayEnd", "ReturnValue"), ("SeaHit", "LineEnd"))
    set_local(g, "SetCursor", F, "Cursor", STRUCT(VECTOR), 1500, 0)
    g.link(("BrClicked", "then"), ("SetCursor", "execute"))
    g.link(("SeaHit", "Intersection"), ("SetCursor", "Cursor"))
    clear_var(g, "NonePicked", [local_var(F, "Picked")], "Picked", OBJ(GRIDACTOR), 1750, 0)
    g.link(("SetCursor", "then"), ("NonePicked", "execute"))

    # the first stand-in under the cursor: its home dock's building
    g.call("Keys", MAPLIB, "Map_Keys", 2000, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", MAP_INT_ACTOR, None), ("Keys", "out", INT_ARRAY_T, None)])
    g.link(("NonePicked", "then"), ("Keys", "execute"))
    g.link(("GetVoyages", "Voyages"), ("Keys", "TargetMap"))
    for_loop_each = for_each(g, "ForIds", INT, 2250, 0)
    g.link(("Keys", "then"), ("ForIds", "Exec"))
    g.link(("Keys", "Keys"), ("ForIds", "Array"))
    map_find(g, "Proxy", ("GetVoyages", "Voyages"), ("ForIds", "Array Element"), MAP_INT_ACTOR, OBJ(ACTOR), 2250, 300, key_type=INT)
    is_valid(g, "ProxyOk", ACTOR, 2500, 450)
    g.link(("Proxy", "Value"), ("ProxyOk", "Object"))
    proxy_loc = actor_loc(g, "ProxyLoc", ("Proxy", "Value"), 2500, 300)
    g.call("CursorDist", MATHLIB, "Vector_Distance2D", 2750, 300,
           [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetCursor", "Cursor"), ("CursorDist", "v1"))
    g.link(proxy_loc, ("CursorDist", "v2"))
    hovered = dmath(g, "Hovered", "LessEqual_DoubleDouble", ("CursorDist", "ReturnValue"), ("GetHover", "HoverRadius"), 3000, 300, out=BOOL)
    is_valid(g, "AlreadyPicked", GRIDACTOR, 2750, 600)
    g.link(("GetPicked", "Picked"), ("AlreadyPicked", "Object"))
    take = bop(g, "Take", "BooleanAND", bop(g, "Under", "BooleanAND", ("ProxyOk", "ReturnValue"), hovered, 3250, 400),
               bnot(g, "FirstOne", ("AlreadyPicked", "ReturnValue"), 3000, 600), 3500, 450)
    branch(g, "BrUnder", 2500, 0)
    g.link(("ForIds", "LoopBody"), ("BrUnder", "execute"))
    g.link(take, ("BrUnder", "Condition"))
    user_call(g, "HomeDock", "DockById", 2750, 0, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("BrUnder", "then"), ("HomeDock", "execute"))
    g.link(("ForIds", "Array Element"), ("HomeDock", "Id"))
    comp_owner(g, "HomeOwner", WORKDOCK, 2750, 750)
    g.link(("HomeDock", "Dock"), ("HomeOwner", "self"))
    g.node("AsBuilding", K2 + "K2Node_DynamicCast",
           [f"TargetType=\"/Script/CoreUObject.Class'{GRIDACTOR}'\"", "PureState=Pure"], 3000, 750,
           [("Object", "in", OBJ(ACTOR), None), ("AsGrid Actor", "out", OBJ(GRIDACTOR), None), ("bSuccess", "out", BOOL, None)])
    g.link(("HomeOwner", "ReturnValue"), ("AsBuilding", "Object"))
    set_local(g, "Pick", F, "Picked", OBJ(GRIDACTOR), 3000, 0)
    g.link(("HomeDock", "then"), ("Pick", "execute"))
    g.link(("AsBuilding", "AsGrid Actor"), ("Pick", "Picked"))
    # found one: pan there
    is_valid(g, "PickedOk", GRIDACTOR, 2500, -300)
    g.link(("GetPicked", "Picked"), ("PickedOk", "Object"))
    # and pan the camera there (the play pawn eases toward its desired pan position), keeping its height
    g.call("Pawn", STATICS, "GetPlayerPawn", 3250, -300,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ("/Script/Engine.Pawn"), None)])
    g.node("AsPlayPawn", K2 + "K2Node_DynamicCast",
           [f"TargetType=\"/Script/CoreUObject.Class'{PLAYPAWN}'\"", "PureState=Pure"], 3500, -300,
           [("Object", "in", OBJ("/Script/Engine.Pawn"), None), ("AsPawn Play", "out", OBJ(PLAYPAWN), None), ("bSuccess", "out", BOOL, None)])
    g.link(("Pawn", "ReturnValue"), ("AsPlayPawn", "Object"))
    get_member(g, "PanNow", PLAYPAWN, "m_desiredPanPos", STRUCT(VECTOR), 3750, -300)
    g.link(("AsPlayPawn", "AsPawn Play"), ("PanNow", "self"))
    _, _, pan_z = break_vec(g, "PanXYZ", ("PanNow", "m_desiredPanPos"), 4000, -300)
    dock_x, dock_y, _ = break_vec(g, "DockXYZ", actor_loc(g, "DockLoc", ("GetPicked", "Picked"), 3750, -150), 4000, -150)
    is_valid(g, "PawnOk", PLAYPAWN, 3750, -600)
    g.link(("AsPlayPawn", "AsPawn Play"), ("PawnOk", "Object"))
    branch(g, "BrPawn", 3250, -450)
    g.link(("ForIds", "Completed"), ("BrPawn", "execute"))
    g.link(bop(g, "CanPan", "BooleanAND", ("PickedOk", "ReturnValue"), ("PawnOk", "ReturnValue"), 4000, -600), ("BrPawn", "Condition"))
    set_member(g, "Pan", PLAYPAWN, "m_desiredPanPos", STRUCT(VECTOR), 3500, -450)
    g.link(("BrPawn", "then"), ("Pan", "execute"))
    g.link(("AsPlayPawn", "AsPawn Play"), ("Pan", "self"))
    g.link(make_vec(g, "PanTo", dock_x, dock_y, pan_z, 4250, -200), ("Pan", "m_desiredPanPos"))
    return g.render()


PROXY_YAW = "-90.0"         # the zoomed-in model's bow is 90 degrees clockwise of its X axis


def set_hidden(g, name, actor_src, hidden, x, y):
    """Hide / show an actor, and turn its collision off / on with it (a hidden ship can't be hovered or clicked).
    Links to (name, "then") come from the collision node."""
    g.call(name, f"/Script/CoreUObject.Class'{ACTOR}'", "SetActorHiddenInGame", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("bNewHidden", "in", BOOL, f'DefaultValue="{"true" if hidden else "false"}"')])
    g.link(actor_src, (name, "self"))
    col = name + "Col"
    g.call(col, f"/Script/CoreUObject.Class'{ACTOR}'", "SetActorEnableCollision", x, y + 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("bNewActorEnableCollision", "in", BOOL, f'DefaultValue="{"false" if hidden else "true"}"')])
    g.link(actor_src, (col, "self"))
    g.link((name, "then"), (col, "execute"))
    g.alias[(name, "then")] = (col, "then")
    return name


def zoomed_child(g, prefix, ship_src, x, y):
    """ship.zoomedActor (ChildActorComponent) -> its child actor and child actor class."""
    get_member(g, prefix + "Zoomed", SHIP, "zoomedActor", OBJ(CHILDCOMP), x, y)
    g.link(ship_src, (prefix + "Zoomed", "self"))
    get_member(g, prefix + "Child", CHILDCOMP, "childActor", OBJ(ACTOR), x + 250, y)
    g.link((prefix + "Zoomed", "zoomedActor"), (prefix + "Child", "self"))
    return (prefix + "Zoomed", "zoomedActor"), (prefix + "Child", "childActor")


def bob_pose(g, p, id_src, pos_src, rot_src, x, y):
    """A stand-in's pose with its bob added: height BobHeight * sin(a), and tilt - the hull rolling BobRoll degrees
    (cos(a)) and the bow pitching BobPitch degrees (sin(a)) - where a = 2 pi t / BobPeriod over game time, offset per
    dock Id so stand-ins don't bob in step. The model's bow is its Y axis, so the actor's pitch rolls the hull and its
    roll pitches the bow. rot_src supplies the yaw. Returns (location, rotation)."""
    get_self(g, p + "Height", "BobHeight", DOUBLE, x, y + 300)
    get_self(g, p + "Period", "BobPeriod", DOUBLE, x, y + 400)
    get_self(g, p + "RollDeg", "BobRoll", DOUBLE, x, y + 500)
    get_self(g, p + "PitchDeg", "BobPitch", DOUBLE, x, y + 600)
    g.call(p + "Time", SYSLIB, "GetGameTimeInSeconds", x, y + 150, [("ReturnValue", "out", DOUBLE, None)])
    omega = dmath(g, p + "Omega", "Divide_DoubleDouble", None, (p + "Period", "BobPeriod"), x + 250, y + 400, a_default="6.283185")
    g.call(p + "IdD", MATHLIB, "Conv_IntToDouble", x + 250, y + 550, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(id_src, (p + "IdD", "inInt"))
    phase = dmath(g, p + "Phase", "Multiply_DoubleDouble", (p + "IdD", "ReturnValue"), None, x + 500, y + 550, b_default="0.731")
    angle = dmath(g, p + "Angle", "Add_DoubleDouble",
                  dmath(g, p + "Wt", "Multiply_DoubleDouble", (p + "Time", "ReturnValue"), omega, x + 500, y + 300), phase, x + 750, y + 300)
    sin_a = dmath1(g, p + "Sin", "Sin", angle, x + 1000, y + 250)
    cos_a = dmath1(g, p + "Cos", "Cos", angle, x + 1000, y + 400)
    lift = dmath(g, p + "Lift", "Multiply_DoubleDouble", (p + "Height", "BobHeight"), sin_a, x + 1250, y + 250)
    g.call(p + "Offset", MATHLIB, "MakeVector", x + 1500, y + 250,
           [("X", "in", DOUBLE, 'DefaultValue="0.0"'), ("Y", "in", DOUBLE, 'DefaultValue="0.0"'), ("Z", "in", DOUBLE, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(lift, (p + "Offset", "Z"))
    g.call(p + "Pos", MATHLIB, "Add_VectorVector", x + 1750, y + 150,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(pos_src, (p + "Pos", "A"))
    g.link((p + "Offset", "ReturnValue"), (p + "Pos", "B"))
    hull = dmath(g, p + "HullRoll", "Multiply_DoubleDouble", (p + "RollDeg", "BobRoll"), cos_a, x + 1250, y + 400)
    bow = dmath(g, p + "BowPitch", "Multiply_DoubleDouble", (p + "PitchDeg", "BobPitch"), sin_a, x + 1250, y + 550)
    g.call(p + "Yaw", MATHLIB, "BreakRotator", x + 1250, y + 700,
           [("InRot", "in", STRUCT(ROTATOR), None), ("Roll", "out", FLOAT, None), ("Pitch", "out", FLOAT, None), ("Yaw", "out", FLOAT, None)])
    g.link(rot_src, (p + "Yaw", "InRot"))
    g.call(p + "Rot", MATHLIB, "MakeRotator", x + 1750, y + 450,
           [("Roll", "in", FLOAT, None), ("Pitch", "in", FLOAT, None), ("Yaw", "in", FLOAT, None), ("ReturnValue", "out", STRUCT(ROTATOR), None)])
    g.link(bow, (p + "Rot", "Roll"))
    g.link(hull, (p + "Rot", "Pitch"))
    g.link((p + "Yaw", "Yaw"), (p + "Rot", "Yaw"))
    return (p + "Pos", "ReturnValue"), (p + "Rot", "ReturnValue")


SPECS = {
    "StandInClick": fn_spec(("BrClicked", "execute"), locals_=[("Cursor", STRUCT(VECTOR)), ("Picked", OBJ(GRIDACTOR))]),
}


GRAPHS = {
    "StandInClick": stand_in_click,
}
