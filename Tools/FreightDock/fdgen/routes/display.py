"""Showing routes (BPL_FDPairing.DrawRoute picks the curve): the route line meshes (SM_RouteStrip), cached route
curves per dock, and the preview course from a dock.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import (
    BOOL, CLASSPIN, DOUBLE, EXEC, INT, MAP_INT_BOOL, MAP_INT_INT, MAP_INT_OBJ, MAP_INT_SHIP, MAP_INT_VECTOR,
    NAME, OBJ, SPLINE_SPACE, STRUCT)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, K2, MATHLIB, MATLIB, MID, ROUTE_LINE_MAT, ROUTE_STRIP, SHIP, SPLINE, SPLINEMESH,
    TRANSFORM, VECTOR, VECTOR2D, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    arrfn, bop, branch, chain, clear_var, for_each, for_loop, get_local, get_self, ii, is_valid, map_add,
    map_find, map_remove, self_var, set_local, set_self, user_call)
from fdgen.routes.course import corner_leg


def show_route_line():
    """ShowRouteLine (Event Tick, after DrawArcs): BPL_FDPairing.DrawRoute leaves the curve to show in WantCurve.
    When that's not the curve already shown, the old line's meshes (ShownMeshes, kept apart from their curve, which may be gone) are
    destroyed and BuildRouteLine makes the new one. WantCurve is cleared for the next frame."""
    g = Graph()
    get_self(g, "GetWant", "WantCurve", OBJ(SPLINE), 0, 400)
    get_self(g, "GetShown", "ShownCurve", OBJ(SPLINE), 0, 500)
    get_self(g, "GetMeshes", "ShownMeshes", OBJ(SPLINEMESH, "Array"), 0, 600)
    OBJT = OBJ("/Script/CoreUObject.Object")
    g.call("Same", MATHLIB, "EqualEqual_ObjectObject", 250, 400,
           [("A", "in", OBJT, None), ("B", "in", OBJT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetWant", "WantCurve"), ("Same", "A"))
    g.link(("GetShown", "ShownCurve"), ("Same", "B"))
    branch(g, "BrSame", 0, 0)
    g.link(("Same", "ReturnValue"), ("BrSame", "Condition"))
    for_each(g, "ForOld", OBJ(SPLINEMESH), 250, 150)
    g.link(("BrSame", "else"), ("ForOld", "Exec"))
    g.link(("GetMeshes", "ShownMeshes"), ("ForOld", "Array"))
    g.call("DropMesh", f"/Script/CoreUObject.Class'{ACTORCOMP}'", "K2_DestroyComponent", 500, 300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTORCOMP), None),
            ("Object", "in", OBJT, None)])
    g.link(("ForOld", "LoopBody"), ("DropMesh", "execute"))
    g.link(("ForOld", "Array Element"), ("DropMesh", "self"))
    arrfn(g, "ClearMeshes", "Array_Clear", 500, 150,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", OBJ(SPLINEMESH, "Array"), None)])
    g.link(("ForOld", "Completed"), ("ClearMeshes", "execute"))
    g.link(("GetMeshes", "ShownMeshes"), ("ClearMeshes", "TargetArray"))
    set_self(g, "SetShown", "ShownCurve", OBJ(SPLINE), 750, 150)
    g.link(("ClearMeshes", "then"), ("SetShown", "execute"))
    g.link(("GetWant", "WantCurve"), ("SetShown", "ShownCurve"))
    is_valid(g, "WantOk", SPLINE, 1000, 400)
    g.link(("GetWant", "WantCurve"), ("WantOk", "Object"))
    branch(g, "BrWant", 1000, 150)
    g.link(("SetShown", "then"), ("BrWant", "execute"))
    g.link(("WantOk", "ReturnValue"), ("BrWant", "Condition"))
    user_call(g, "Build", "BuildRouteLine", 1250, 150, ins=[("Curve", OBJ(SPLINE))])
    g.link(("BrWant", "then"), ("Build", "execute"))
    g.link(("GetWant", "WantCurve"), ("Build", "Curve"))
    clear_var(g, "ClearWant", [self_var("WantCurve")], "WantCurve", OBJ(SPLINE), 1500, 0)
    for src in (("BrSame", "then"), ("BrWant", "else"), ("Build", "then")):
        g.link(src, ("ClearWant", "execute"))
    return g.render()


def build_route_line():
    """BuildRouteLine(Curve): one spline mesh (SM_RouteStrip, RouteLineWidth wide, RouteLineHeight above the curve,
    RouteLineColor via the shared RouteLineMID) per segment of Curve, in world space, added to ShownMeshes."""
    g = Graph()
    F = "BuildRouteLine"
    SPL = f"/Script/CoreUObject.Class'{SPLINE}'"
    SMC = f"/Script/CoreUObject.Class'{SPLINEMESH}'"
    PRIM = "/Script/CoreUObject.Class'/Script/Engine.PrimitiveComponent'"
    get_local(g, "GetCurve", F, "Curve", OBJ(SPLINE), 0, 400)
    get_self(g, "GetMID", "RouteLineMID", OBJ(MID), 0, 500)
    get_self(g, "GetColor", "RouteLineColor", STRUCT("/Script/CoreUObject.LinearColor"), 0, 600)
    get_self(g, "GetWidth", "RouteLineWidth", DOUBLE, 0, 700)
    get_self(g, "GetHeight", "RouteLineHeight", DOUBLE, 0, 800)
    get_self(g, "GetMeshes", "ShownMeshes", OBJ(SPLINEMESH, "Array"), 0, 900)
    curve, mid = ("GetCurve", "Curve"), ("GetMID", "RouteLineMID")

    # the shared material instance, coloured RouteLineColor
    is_valid(g, "HasMID", MID, 250, 300)
    g.link(mid, ("HasMID", "Object"))
    branch(g, "BrMID", 0, 0)
    g.link(("HasMID", "ReturnValue"), ("BrMID", "Condition"))
    g.call("NewMID", MATLIB, "CreateDynamicMaterialInstance", 250, -200,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Parent", "in", OBJ("/Script/Engine.MaterialInterface"), f"DefaultObject=\"/Script/Engine.Material'{ROUTE_LINE_MAT}'\""),
            ("OptionalName", "in", NAME, 'DefaultValue="None"'), ("ReturnValue", "out", OBJ(MID), None)])
    g.link(("BrMID", "else"), ("NewMID", "execute"))
    set_self(g, "SetMID", "RouteLineMID", OBJ(MID), 500, -200)
    g.link(("NewMID", "then"), ("SetMID", "execute"))
    g.link(("NewMID", "ReturnValue"), ("SetMID", "RouteLineMID"))
    g.call("Tint", f"/Script/CoreUObject.Class'{MID}'", "SetVectorParameterValue", 750, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MID), None),
            ("ParameterName", "in", NAME, 'DefaultValue="Color"'),
            ("Value", "in", STRUCT("/Script/CoreUObject.LinearColor"), None)])
    g.link(("BrMID", "then"), ("Tint", "execute"))
    g.link(("SetMID", "then"), ("Tint", "execute"))
    g.link(mid, ("Tint", "self"))
    g.link(("GetColor", "RouteLineColor"), ("Tint", "Value"))

    # one mesh per segment
    g.call("NPts", SPL, "GetNumberOfSplinePoints", 1000, 300, [("self", "in", OBJ(SPLINE), None), ("ReturnValue", "out", INT, None)])
    g.link(curve, ("NPts", "self"))
    last = ii(g, "LastSeg", "Subtract_IntInt", ("NPts", "ReturnValue"), None, 1250, 300, b_default="2")
    for_loop(g, "ForSegs", 1000, 0, first=0)
    g.link(last, ("ForSegs", "LastIndex"))
    g.link(("Tint", "then"), ("ForSegs", "Exec"))
    nxt = ii(g, "NextPt", "Add_IntInt", ("ForSegs", "Index"), None, 1250, 450, b_default="1")
    g.call("Lift", MATHLIB, "MakeVector", 1250, 600,
           [("X", "in", DOUBLE, 'DefaultValue="0.0"'), ("Y", "in", DOUBLE, 'DefaultValue="0.0"'), ("Z", "in", DOUBLE, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("GetHeight", "RouteLineHeight"), ("Lift", "Z"))
    ends = {}
    for end, idx, y in (("Start", ("ForSegs", "Index"), 750), ("End", nxt, 1000)):
        g.call(end + "Loc", SPL, "GetLocationAtSplinePoint", 1500, y,
               [("self", "in", OBJ(SPLINE), None), ("PointIndex", "in", INT, None),
                ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link(curve, (end + "Loc", "self"))
        g.link(idx, (end + "Loc", "PointIndex"))
        g.call(end + "Pos", MATHLIB, "Add_VectorVector", 1750, y,
               [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link((end + "Loc", "ReturnValue"), (end + "Pos", "A"))
        g.link(("Lift", "ReturnValue"), (end + "Pos", "B"))
        tan_fn = "GetLeaveTangentAtSplinePoint" if end == "Start" else "GetArriveTangentAtSplinePoint"
        g.call(end + "Tan", SPL, tan_fn, 1500, y + 150,
               [("self", "in", OBJ(SPLINE), None), ("PointIndex", "in", INT, None),
                ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link(curve, (end + "Tan", "self"))
        g.link(idx, (end + "Tan", "PointIndex"))
        ends[end] = ((end + "Pos", "ReturnValue"), (end + "Tan", "ReturnValue"))

    ctype, cdefault = CLASSPIN(ACTORCOMP, SPLINEMESH)
    g.node("NewMesh", K2 + "K2Node_AddComponentByClass", [], 1250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("Class", "in", ctype, cdefault), ("bManualAttachment", "in", BOOL, 'DefaultValue="false"'),
            ("RelativeTransform", "in", STRUCT(TRANSFORM), None), ("ReturnValue", "out", OBJ(SPLINEMESH), None)])
    g.link(("ForSegs", "LoopBody"), ("NewMesh", "execute"))
    mesh = ("NewMesh", "ReturnValue")
    steps = []

    def step(name, cls, func, pins, x):
        g.call(name, cls, func, x, 0, [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINEMESH), None)] + pins)
        g.link(mesh, (name, "self"))
        steps.append(name)

    # spline meshes default to Static, and a Static component refuses SetStaticMesh once play has begun
    step("Movable", f"/Script/CoreUObject.Class'/Script/Engine.SceneComponent'", "SetMobility",
         [("NewMobility", "in", ['PinType.PinCategory="byte"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/Engine.EComponentMobility'\""],
           'DefaultValue="Movable"')], 1400)
    # world space regardless of where the actor is
    step("Absolute", f"/Script/CoreUObject.Class'/Script/Engine.SceneComponent'", "SetAbsolute",
         [("bNewAbsoluteLocation", "in", BOOL, 'DefaultValue="true"'), ("bNewAbsoluteRotation", "in", BOOL, 'DefaultValue="true"'),
          ("bNewAbsoluteScale", "in", BOOL, 'DefaultValue="true"')], 1500)
    step("SetStrip", "/Script/CoreUObject.Class'/Script/Engine.StaticMeshComponent'", "SetStaticMesh",
         [("NewMesh", "in", OBJ("/Script/Engine.StaticMesh"), f"DefaultObject=\"/Script/Engine.StaticMesh'{ROUTE_STRIP}'\""),
          ("ReturnValue", "out", BOOL, None)], 1750)
    step("SetMat", PRIM, "SetMaterial",
         [("ElementIndex", "in", INT, 'DefaultValue="0"'), ("Material", "in", OBJ("/Script/Engine.MaterialInterface"), None)], 2000)
    g.link(mid, ("SetMat", "Material"))
    step("NoCollide", PRIM, "SetCollisionEnabled",
         [("NewType", "in", ['PinType.PinCategory="byte"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/Engine.ECollisionEnabled'\""],
           'DefaultValue="NoCollision"')], 2250)
    step("NoShadow", PRIM, "SetCastShadow", [("NewCastShadow", "in", BOOL, 'DefaultValue="false"')], 2500)
    step("Shape", SMC, "SetStartAndEnd",
         [("StartPos", "in", STRUCT(VECTOR), None), ("StartTangent", "in", STRUCT(VECTOR), None),
          ("EndPos", "in", STRUCT(VECTOR), None), ("EndTangent", "in", STRUCT(VECTOR), None),
          ("bUpdateMesh", "in", BOOL, 'DefaultValue="false"')], 2750)
    g.link(ends["Start"][0], ("Shape", "StartPos"))
    g.link(ends["Start"][1], ("Shape", "StartTangent"))
    g.link(ends["End"][0], ("Shape", "EndPos"))
    g.link(ends["End"][1], ("Shape", "EndTangent"))
    g.call("Scale", MATHLIB, "MakeVector2D", 2750, 400,
           [("X", "in", DOUBLE, None), ("Y", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", STRUCT(VECTOR2D), None)])
    g.link(("GetWidth", "RouteLineWidth"), ("Scale", "X"))
    for end, x, update in (("Start", 3000, "false"), ("End", 3250, "true")):
        step(f"{end}Scale", SMC, f"Set{end}Scale",
             [(f"{end}Scale", "in", STRUCT(VECTOR2D), None), ("bUpdateMesh", "in", BOOL, f'DefaultValue="{update}"')], x)
        g.link(("Scale", "ReturnValue"), (f"{end}Scale", f"{end}Scale"))
    chain(g, "NewMesh", *steps)
    arrfn(g, "Keep", "Array_Add", 3500, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", OBJ(SPLINEMESH, "Array"), None),
           ("NewItem", "in", OBJ(SPLINEMESH), None), ("ReturnValue", "out", INT, None)])
    g.link((steps[-1], "then"), ("Keep", "execute"))
    g.link(("GetMeshes", "ShownMeshes"), ("Keep", "TargetArray"))
    g.link(mesh, ("Keep", "NewItem"))
    return g.render()


def route_curve():
    """RouteCurve(Id) -> Curve: dock Id's route as a spline, cached in RouteCurves (PlanRoute drops it via
    DropRouteCurve). Built like MakeCourse's: the route points, each leg cut into CourseSpacing steps, corners rounded.
    Local: CurveSpline (Spline Component). Wire UseCached.then and Store.then -> Return, GetCurveForReturn -> Curve."""
    g = Graph()
    F = "RouteCurve"
    SPL = f"/Script/CoreUObject.Class'{SPLINE}'"
    get_local(g, "GetId", F, "Id", INT, 0, 400)
    get_local(g, "GetCurve", F, "CurveSpline", OBJ(SPLINE), 0, 500)
    get_self(g, "GetRoutePts", "RoutePts", MAP_INT_VECTOR, 0, 600)
    get_self(g, "GetRouteLen", "RouteLen", MAP_INT_INT, 0, 700)
    get_self(g, "GetCurves", "RouteCurves", MAP_INT_OBJ(SPLINE), 0, 800)
    get_self(g, "GetSpacing", "CourseSpacing", DOUBLE, 0, 900)
    key, course = ("GetId", "Id"), ("GetCurve", "CurveSpline")
    map_find(g, "Cached", ("GetCurves", "RouteCurves"), key, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), 250, 300, key_type=INT)
    is_valid(g, "HasCached", SPLINE, 500, 300)
    g.link(("Cached", "Value"), ("HasCached", "Object"))
    branch(g, "BrCached", 0, 0)
    g.link(("HasCached", "ReturnValue"), ("BrCached", "Condition"))
    set_local(g, "UseCached", F, "CurveSpline", OBJ(SPLINE), 250, -200)
    g.link(("BrCached", "then"), ("UseCached", "execute"))
    g.link(("Cached", "Value"), ("UseCached", "CurveSpline"))

    ctype, cdefault = CLASSPIN(ACTORCOMP, SPLINE)
    g.node("NewSpline", K2 + "K2Node_AddComponentByClass", [], 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("Class", "in", ctype, cdefault), ("bManualAttachment", "in", BOOL, 'DefaultValue="false"'),
            ("RelativeTransform", "in", STRUCT(TRANSFORM), None), ("ReturnValue", "out", OBJ(SPLINE), None)])
    g.link(("BrCached", "else"), ("NewSpline", "execute"))
    set_local(g, "SetCurve", F, "CurveSpline", OBJ(SPLINE), 500, 0)
    g.link(("NewSpline", "then"), ("SetCurve", "execute"))
    g.link(("NewSpline", "ReturnValue"), ("SetCurve", "CurveSpline"))
    g.call("ClearPts", SPL, "ClearSplinePoints", 750, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None),
            ("bUpdateSpline", "in", BOOL, 'DefaultValue="false"')])
    g.link(("SetCurve", "then"), ("ClearPts", "execute"))
    g.link(course, ("ClearPts", "self"))

    def add_point(name, pos_src, x, y):
        g.call(name, SPL, "AddSplinePoint", x, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None),
                ("position", "in", STRUCT(VECTOR), None), ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'),
                ("bUpdateSpline", "in", BOOL, 'DefaultValue="false"')])
        g.link(course, (name, "self"))
        g.link(pos_src, (name, "position"))

    base = ii(g, "Base", "Multiply_IntInt", key, None, 750, 450, b_default="1000")
    map_find(g, "Pt0", ("GetRoutePts", "RoutePts"), base, MAP_INT_VECTOR, STRUCT(VECTOR), 1000, 450, key_type=INT)
    add_point("PtFirst", ("Pt0", "Value"), 1000, 0)
    g.link(("ClearPts", "then"), ("PtFirst", "execute"))
    map_find(g, "N", ("GetRouteLen", "RouteLen"), key, MAP_INT_INT, INT, 1000, 600, key_type=INT)
    last_leg = ii(g, "LastLeg", "Subtract_IntInt", ("N", "Value"), None, 1250, 600, b_default="2")
    for_loop(g, "ForLegs", 1250, 0, first=0)
    g.link(last_leg, ("ForLegs", "LastIndex"))
    g.link(("PtFirst", "then"), ("ForLegs", "Exec"))
    sa = ii(g, "SlotA", "Add_IntInt", base, ("ForLegs", "Index"), 1500, 450)
    sb = ii(g, "SlotB", "Add_IntInt", sa, None, 1750, 450, b_default="1")
    map_find(g, "LegA", ("GetRoutePts", "RoutePts"), sa, MAP_INT_VECTOR, STRUCT(VECTOR), 1750, 600, key_type=INT)
    map_find(g, "LegB", ("GetRoutePts", "RoutePts"), sb, MAP_INT_VECTOR, STRUCT(VECTOR), 2000, 600, key_type=INT)
    a, b = ("LegA", "Value"), ("LegB", "Value")
    get_self(g, "GetCorner", "CornerRadius", DOUBLE, 0, 1000)
    corner_leg(g, a, b, ("ForLegs", "Index"), last_leg, ("GetSpacing", "CourseSpacing"), ("GetCorner", "CornerRadius"),
               ("ForLegs", "LoopBody"), add_point, 1500, 900)

    g.call("Finish", SPL, "UpdateSpline", 1500, -300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None)])
    user_call(g, "Smooth", "SmoothTangents", 0, -450, ins=[("Spline", OBJ(SPLINE))])
    g.link(("ForLegs", "Completed"), ("Smooth", "execute"))
    g.link(course, ("Smooth", "Spline"))
    g.link(("Smooth", "then"), ("Finish", "execute"))
    g.link(course, ("Finish", "self"))
    map_add(g, "Store", ("GetCurves", "RouteCurves"), key, course, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), 1750, -300, key_type=INT)
    g.link(("Finish", "then"), ("Store", "execute"))
    get_local(g, "GetCurveForReturn", F, "CurveSpline", OBJ(SPLINE), 2000, -450)
    return g.render()


def drop_spline(g, p, map_var, key_src, after, x, y):
    """Destroy map_var[key] (a spline) if it's there and remove the entry; returns the last exec output."""
    get_self(g, p + "Get", map_var, MAP_INT_OBJ(SPLINE), x, y + 300)
    map_find(g, p + "Old", (p + "Get", map_var), key_src, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), x + 250, y + 300, key_type=INT)
    is_valid(g, p + "OldOk", SPLINE, x + 500, y + 300)
    g.link((p + "Old", "Value"), (p + "OldOk", "Object"))
    branch(g, p + "BrOld", x, y)
    g.link(after, (p + "BrOld", "execute"))
    g.link((p + "OldOk", "ReturnValue"), (p + "BrOld", "Condition"))
    g.call(p + "Destroy", f"/Script/CoreUObject.Class'{ACTORCOMP}'", "K2_DestroyComponent", x + 250, y - 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTORCOMP), None),
            ("Object", "in", OBJ("/Script/CoreUObject.Object"), None)])
    g.link((p + "BrOld", "then"), (p + "Destroy", "execute"))
    g.link((p + "Old", "Value"), (p + "Destroy", "self"))
    map_remove(g, p + "Forget", (p + "Get", map_var), key_src, MAP_INT_OBJ(SPLINE), x + 500, y)
    g.link((p + "Destroy", "then"), (p + "Forget", "execute"))
    g.link((p + "BrOld", "else"), (p + "Forget", "execute"))
    return (p + "Forget", "then")


def drop_route_curve():
    """DropRouteCurve(Id): destroy dock Id's cached route curve and preview course (its route changed)."""
    g = Graph()
    get_local(g, "GetId", "DropRouteCurve", "Id", INT, 0, 400)
    g.node("Start", K2 + "K2Node_ExecutionSequence", [], 0, 0, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
    after = drop_spline(g, "Curve", "RouteCurves", ("GetId", "Id"), ("Start", "then_0"), 250, 0)
    drop_spline(g, "Preview", "PreviewCourses", ("GetId", "Id"), after, 1000, 0)
    return g.render()


def preview_course():
    """PreviewCourse(Id, ToHome) -> Curve: the course dock Id's ship would take next (MakeCourse) - outbound from its
    berth, or homeward when ToHome - cached in PreviewCourses / PreviewHomes until the route changes
    (DropRouteCurve) or the direction does. None if the dock has no ship.
    Locals: Ship (Nautical Ship), Picked (Spline Component). Wire Done -> Return, GetCurveForReturn -> Curve."""
    g = Graph()
    F = "PreviewCourse"
    get_local(g, "GetId", F, "Id", INT, 0, 400)
    get_local(g, "GetToHome", F, "ToHome", BOOL, 0, 500)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 600)
    get_self(g, "GetPreviews", "PreviewCourses", MAP_INT_OBJ(SPLINE), 0, 700)
    get_self(g, "GetHomes", "PreviewHomes", MAP_INT_BOOL, 0, 800)
    get_self(g, "GetVShip", "VoyageShip", MAP_INT_SHIP, 0, 900)
    key, to_home = ("GetId", "Id"), ("GetToHome", "ToHome")
    g.node("Done", K2 + "K2Node_ExecutionSequence", [], 3000, 0, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])

    # cached, same direction: use it
    map_find(g, "Cached", ("GetPreviews", "PreviewCourses"), key, MAP_INT_OBJ(SPLINE), OBJ(SPLINE), 250, 300, key_type=INT)
    map_find(g, "CachedHome", ("GetHomes", "PreviewHomes"), key, MAP_INT_BOOL, BOOL, 250, 450, key_type=INT)
    is_valid(g, "CachedOk", SPLINE, 500, 300)
    g.link(("Cached", "Value"), ("CachedOk", "Object"))
    g.call("SameWay", MATHLIB, "EqualEqual_BoolBool", 500, 450,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("CachedHome", "Value"), ("SameWay", "A"))
    g.link(to_home, ("SameWay", "B"))
    branch(g, "BrCached", 0, 0)
    g.link(bop(g, "UseCache", "BooleanAND", ("CachedOk", "ReturnValue"), ("SameWay", "ReturnValue"), 750, 350), ("BrCached", "Condition"))
    set_local(g, "UseCached", F, "Picked", OBJ(SPLINE), 250, -200)
    g.link(("BrCached", "then"), ("UseCached", "execute"))
    g.link(("Cached", "Value"), ("UseCached", "Picked"))
    g.link(("UseCached", "then"), ("Done", "execute"))

    # otherwise drop the old one and build: homeward with the voyage's ship, outbound with the ship berthed at the dock
    after = drop_spline(g, "Drop", "PreviewCourses", key, ("BrCached", "else"), 250, 100)
    branch(g, "BrHome", 750, 100)
    g.link(after, ("BrHome", "execute"))
    g.link(to_home, ("BrHome", "Condition"))
    map_find(g, "VShip", ("GetVShip", "VoyageShip"), key, MAP_INT_SHIP, OBJ(SHIP), 1000, 400, key_type=INT)
    set_local(g, "ShipHome", F, "Ship", OBJ(SHIP), 1000, -50)
    g.link(("BrHome", "then"), ("ShipHome", "execute"))
    g.link(("VShip", "Value"), ("ShipHome", "Ship"))
    user_call(g, "Dock", "DockById", 1000, 200, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("BrHome", "else"), ("Dock", "execute"))
    g.link(key, ("Dock", "Id"))
    user_call(g, "Berthed", "ShipAtDock", 1250, 200, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Ship", OBJ(SHIP))])
    g.link(("Dock", "then"), ("Berthed", "execute"))
    g.link(("Dock", "Dock"), ("Berthed", "Dock"))
    set_local(g, "ShipOut", F, "Ship", OBJ(SHIP), 1500, 200)
    g.link(("Berthed", "then"), ("ShipOut", "execute"))
    g.link(("Berthed", "Ship"), ("ShipOut", "Ship"))
    is_valid(g, "ShipOk", SHIP, 1750, 400)
    g.link(("GetShip", "Ship"), ("ShipOk", "Object"))
    branch(g, "BrShip", 1750, 100)
    g.link(("ShipHome", "then"), ("BrShip", "execute"))
    g.link(("ShipOut", "then"), ("BrShip", "execute"))
    g.link(("ShipOk", "ReturnValue"), ("BrShip", "Condition"))
    user_call(g, "Make", "MakeCourse", 2000, 0, ins=[("Id", INT), ("Ship", OBJ(SHIP)), ("ToHome", BOOL)], outs=[("Course", OBJ(SPLINE))])
    g.link(("BrShip", "then"), ("Make", "execute"))
    g.link(key, ("Make", "Id"))
    g.link(("GetShip", "Ship"), ("Make", "Ship"))
    g.link(to_home, ("Make", "ToHome"))
    map_add(g, "Keep", ("GetPreviews", "PreviewCourses"), key, ("Make", "Course"), MAP_INT_OBJ(SPLINE), OBJ(SPLINE), 2250, 0, key_type=INT)
    g.link(("Make", "then"), ("Keep", "execute"))
    map_add(g, "KeepHome", ("GetHomes", "PreviewHomes"), key, to_home, MAP_INT_BOOL, BOOL, 2500, 0, key_type=INT)
    g.link(("Keep", "then"), ("KeepHome", "execute"))
    set_local(g, "UseNew", F, "Picked", OBJ(SPLINE), 2750, 0)
    g.link(("KeepHome", "then"), ("UseNew", "execute"))
    g.link(("Make", "Course"), ("UseNew", "Picked"))
    g.link(("UseNew", "then"), ("Done", "execute"))
    clear_var(g, "NoCurve", [local_var(F, "Picked")], "Picked", OBJ(SPLINE), 2000, 300)
    g.link(("BrShip", "else"), ("NoCurve", "execute"))
    g.link(("NoCurve", "then"), ("Done", "execute"))
    get_local(g, "GetCurveForReturn", F, "Picked", OBJ(SPLINE), 3000, 300)
    return g.render()


SPECS = {
    "RouteCurve": fn_spec(("BrCached", "execute"), inputs=[("Id", INT)], outputs=[("Curve", OBJ(SPLINE))],
                          locals_=[("CurveSpline", OBJ(SPLINE))],
                          returns=[("UseCached", "then"), ("Store", "then")],
                          values=[("GetCurveForReturn", "CurveSpline", "Curve")]),
    "DropRouteCurve": fn_spec(("Start", "execute"), inputs=[("Id", INT)]),
    "PreviewCourse": fn_spec(("BrCached", "execute"), inputs=[("Id", INT), ("ToHome", BOOL)], outputs=[("Curve", OBJ(SPLINE))],
                             locals_=[("Ship", OBJ(SHIP)), ("Picked", OBJ(SPLINE))], returns=[("Done", "then_0")],
                             values=[("GetCurveForReturn", "Picked", "Curve")]),
    "ShowRouteLine": fn_spec(("BrSame", "execute")),
    "BuildRouteLine": fn_spec(("BrMID", "execute"), inputs=[("Curve", OBJ(SPLINE))]),
}


GRAPHS = {
    "RouteCurve": route_curve,
    "DropRouteCurve": drop_route_curve,
    "PreviewCourse": preview_course,
    "ShowRouteLine": show_route_line,
    "BuildRouteLine": build_route_line,
}
