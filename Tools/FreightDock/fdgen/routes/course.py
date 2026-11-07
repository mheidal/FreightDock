"""Turning a cell path into a sailable course: turn arcs at corners, the waiting heading, smoothed spline
tangents, and MakeCourse, which builds the voyage spline.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import (
    BOOL, CLASSPIN, DOUBLE, EXEC, FLOAT, INT, OBJ,
    SPLINE_SPACE, STRUCT)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, K2, MATHLIB, NDOCK, NDOCKSTATE, SHIP, SPLINE, TRANSFORM,
    VECTOR, VOYAGE_LIB, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    bop, break_struct, break_vec, dmath,
    dmath1, for_loop, get_local, get_member, ii, loom_call, user_call)


def corner_leg(g, a, b, leg_src, last_leg_src, spacing_src, radius_src, body, add_point, x, y):
    """Spline points along one leg a -> b, every CourseSpacing, for MakeCourse / RouteCurve. Each end that meets
    another leg is cut back by R = min(CornerRadius, half the leg), so the spline curves round the corner instead
    of through it. The leg's start point is added unless it's the first leg (already added) or uncut. A leg used
    up by its two cuts adds just that one point (its midpoint), never a duplicate, which would leave a cusp."""
    def dd(name, func, a_src, b_src, xx, yy, b_default=None):
        g.call(name, MATHLIB, func, xx, yy,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None if b_default is None else f'DefaultValue="{b_default}"'),
                ("ReturnValue", "out", DOUBLE, None)])
        g.link(a_src, (name, "A"))
        if b_src:
            g.link(b_src, (name, "B"))
        return (name, "ReturnValue")

    def pick(name, a_src, b_default, cond, xx, yy):
        g.call(name, MATHLIB, "SelectFloat", xx, yy,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, f'DefaultValue="{b_default}"'), ("bPickA", "in", BOOL, None),
                ("ReturnValue", "out", DOUBLE, None)])
        g.link(a_src, (name, "A"))
        g.link(cond, (name, "bPickA"))
        return (name, "ReturnValue")

    g.call("LegLen", MATHLIB, "Vector_Distance2D", x, y,
           [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(a, ("LegLen", "v1"))
    g.link(b, ("LegLen", "v2"))
    length = dd("Len1", "FMax", ("LegLen", "ReturnValue"), None, x + 250, y, b_default="1.0")
    half = dd("Half", "Multiply_DoubleDouble", length, None, x + 500, y, b_default="0.5")
    r = dd("R", "FMin", radius_src, half, x + 750, y)
    trim = dd("TrimT", "Divide_DoubleDouble", r, length, x + 1000, y)
    not_first = ii(g, "NotFirst", "Greater_IntInt", leg_src, None, x, y + 150, b_default="0", out=BOOL)
    not_last = ii(g, "NotLast", "Less_IntInt", leg_src, last_leg_src, x, y + 300, out=BOOL)
    t0 = pick("T0", trim, "0.0", (not_first), x + 1250, y)
    cut1 = pick("Cut1", trim, "0.0", (not_last), x + 1250, y + 150)
    g.call("T1", MATHLIB, "Subtract_DoubleDouble", x + 1500, y + 150,
           [("A", "in", DOUBLE, 'DefaultValue="1.0"'), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(cut1, ("T1", "B"))
    span = dd("Span", "Subtract_DoubleDouble", ("T1", "ReturnValue"), t0, x + 1750, y)
    span_len = dd("SpanLen", "Multiply_DoubleDouble", span, length, x + 2000, y)
    spare = dd("Spare", "Subtract_DoubleDouble", span_len, None, x + 2000, y + 150, b_default="1.0")
    spare = dd("SpareMin0", "FMax", spare, None, x + 2250, y + 150, b_default="0.0")
    steps = dd("Steps", "Divide_DoubleDouble", spare, spacing_src, x + 2250, y)
    g.call("NSteps", MATHLIB, "FCeil", x + 2750, y, [("A", "in", DOUBLE, None), ("ReturnValue", "out", INT, None)])
    g.link(steps, ("NSteps", "A"))
    nsteps1 = ii(g, "NSteps1", "Max", ("NSteps", "ReturnValue"), None, x + 2750, y + 150, b_default="1")
    g.call("Cut", MATHLIB, "GreaterEqual_DoubleDouble", x + 1000, y + 300,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", BOOL, None)])
    g.link(r, ("Cut", "A"))
    with_start = bop(g, "WithStart", "BooleanAND", not_first, ("Cut", "ReturnValue"), x + 1250, y + 300)
    g.call("FirstStep", MATHLIB, "SelectInt", x + 1500, y + 300,
           [("A", "in", INT, 'DefaultValue="0"'), ("B", "in", INT, 'DefaultValue="1"'), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", INT, None)])
    g.link(with_start, ("FirstStep", "bPickA"))
    for_loop(g, "ForSteps", x, y - 450)
    g.link(("FirstStep", "ReturnValue"), ("ForSteps", "FirstIndex"))
    g.link(("NSteps", "ReturnValue"), ("ForSteps", "LastIndex"))
    g.link(body, ("ForSteps", "Exec"))
    g.call("StepD", MATHLIB, "Conv_IntToDouble", x, y + 450, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("ForSteps", "Index"), ("StepD", "inInt"))
    g.call("NStepsD", MATHLIB, "Conv_IntToDouble", x + 3000, y, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(nsteps1, ("NStepsD", "inInt"))
    frac = dd("Frac", "Divide_DoubleDouble", ("StepD", "ReturnValue"), ("NStepsD", "ReturnValue"), x + 250, y + 450)
    along = dd("Along", "Multiply_DoubleDouble", frac, span, x + 500, y + 450)
    alpha = dd("Alpha", "Add_DoubleDouble", t0, along, x + 750, y + 450)
    g.call("StepPos", MATHLIB, "VLerp", x + 1000, y + 450,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("Alpha", "in", FLOAT, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(a, ("StepPos", "A"))
    g.link(b, ("StepPos", "B"))
    g.link(alpha, ("StepPos", "Alpha"))
    add_point("PtStep", ("StepPos", "ReturnValue"), x + 250, y - 450)
    g.link(("ForSteps", "LoopBody"), ("PtStep", "execute"))


def wait_heading():
    """WaitHeading(Id, HomeFwd) -> Fwd: the heading dock Id's stand-in waits in at the target's stand-off point -
    the target berth's out-direction turned by the same angle as from Id's berth out-direction to its berthed ship's
    bow (HomeFwd), i.e. as a ship berthed at the target would face. The target is found by pairing (TargetOf), so
    this works between voyages too. Wire LookUp.then -> Return, Turned -> Fwd."""
    g = Graph()
    F = "WaitHeading"
    get_local(g, "GetId", F, "Id", INT, 0, 400)
    get_local(g, "GetHomeFwd", F, "HomeFwd", STRUCT(VECTOR), 0, 500)
    outs = {}
    user_call(g, "HomeDock", "DockById", 0, 0, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("GetId", "Id"), ("HomeDock", "Id"))
    user_call(g, "AwayDock", "TargetOf", 500, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Target", OBJ(WORKDOCK))])
    g.link(("HomeDock", "Dock"), ("AwayDock", "Dock"))
    g.link(("HomeDock", "then"), ("AwayDock", "execute"))
    prev = "AwayDock"
    for i, (who, dock_src) in enumerate((("Home", ("HomeDock", "Dock")), ("Away", ("AwayDock", "Target")))):
        x = 500 * i
        user_call(g, who + "Berth", "NauticalDockAt", x + 750, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Best", OBJ(NDOCK))])
        g.link(dock_src, (who + "Berth", "Dock"))
        g.link((prev, "then"), (who + "Berth", "execute"))
        prev = who + "Berth"
        get_member(g, who + "State", NDOCK, "State", STRUCT(NDOCKSTATE), x + 250, 300)
        g.link((who + "Berth", "Best"), (who + "State", "self"))
        break_struct(g, who + "Break", NDOCKSTATE, [("berthOutDirection", STRUCT(VECTOR))], x + 250, 450)
        g.link((who + "State", "State"), (who + "Break", "NauticalDockState"))
        outs[who] = (who + "Break", "berthOutDirection")
    g.node("LookUp", K2 + "K2Node_ExecutionSequence", [], 1250, 0, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
    g.link((prev, "then"), ("LookUp", "execute"))
    # signed angle (degrees) from the home out-direction to the home bow, in the XY plane
    ox, oy, _ = break_vec(g, "OutXY", outs["Home"], 500, 800)
    fx, fy, _ = break_vec(g, "FwdXY", ("GetHomeFwd", "HomeFwd"), 500, 950)
    cross = dmath(g, "Cross", "Subtract_DoubleDouble", dmath(g, "OxFy", "Multiply_DoubleDouble", ox, fy, 750, 800),
                  dmath(g, "OyFx", "Multiply_DoubleDouble", oy, fx, 750, 950), 1000, 800)
    dot = dmath(g, "Dot", "Add_DoubleDouble", dmath(g, "OxFx", "Multiply_DoubleDouble", ox, fx, 750, 1100),
                dmath(g, "OyFy", "Multiply_DoubleDouble", oy, fy, 750, 1250), 1000, 1100)
    ang = dmath1(g, "AngDeg", "RadiansToDegrees", dmath(g, "Ang", "Atan2", cross, dot, 1250, 900, pins=("Y", "X")), 1500, 900)
    g.call("Turned", MATHLIB, "RotateAngleAxis", 1750, 600,
           [("InVect", "in", STRUCT(VECTOR), None), ("AngleDeg", "in", DOUBLE, None),
            ("Axis", "in", STRUCT(VECTOR), 'DefaultValue="0.000000,0.000000,1.000000"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(outs["Away"], ("Turned", "InVect"))
    g.link(ang, ("Turned", "AngleDeg"))
    return g.render()


def smooth_tangents():
    """SmoothTangents(Spline): give every point explicit tangents - along the line from the previous point to the
    next, arriving as long as the gap before it and leaving as long as the gap after (the first and last points use
    their one gap both ways). The spline's own tangents assume evenly spaced points; ours aren't (straights, corner
    cuts, arc steps), and where gaps differ it overshoots into small bulges and S-bends. Call before UpdateSpline."""
    g = Graph()
    F = "SmoothTangents"
    SPL = f"/Script/CoreUObject.Class'{SPLINE}'"
    get_local(g, "GetSpline", F, "Spline", OBJ(SPLINE), 0, 400)
    spl = ("GetSpline", "Spline")
    g.call("NPts", SPL, "GetNumberOfSplinePoints", 250, 400, [("self", "in", OBJ(SPLINE), None), ("ReturnValue", "out", INT, None)])
    g.link(spl, ("NPts", "self"))
    last = ii(g, "Last", "Subtract_IntInt", ("NPts", "ReturnValue"), None, 500, 400, b_default="1")
    for_loop(g, "ForPts", 0, 0, first=0)
    g.link(last, ("ForPts", "LastIndex"))
    i = ("ForPts", "Index")
    prev_i = ii(g, "PrevI", "Max", ii(g, "IMinus", "Subtract_IntInt", i, None, 250, 600, b_default="1"), None, 500, 600, b_default="0")
    next_i = ii(g, "NextI", "Min", ii(g, "IPlus", "Add_IntInt", i, None, 250, 750, b_default="1"), last, 500, 750)

    def loc(name, idx, y):
        g.call(name, SPL, "GetLocationAtSplinePoint", 750, y,
               [("self", "in", OBJ(SPLINE), None), ("PointIndex", "in", INT, None),
                ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link(spl, (name, "self"))
        g.link(idx, (name, "PointIndex"))
        return (name, "ReturnValue")

    here, prev, nxt = loc("Here", i, 450), loc("Prev", prev_i, 600), loc("Next", next_i, 750)
    g.call("Span", MATHLIB, "Subtract_VectorVector", 1000, 650,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(nxt, ("Span", "A"))
    g.link(prev, ("Span", "B"))
    g.call("Dir", MATHLIB, "Normal", 1250, 650,
           [("A", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(("Span", "ReturnValue"), ("Dir", "A"))
    gaps = {}
    for name, a, b, y in (("GapIn", here, prev, 850), ("GapOut", nxt, here, 950)):
        g.call(name, MATHLIB, "Vector_Distance", 1000, y,
               [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(a, (name, "v1"))
        g.link(b, (name, "v2"))
        gaps[name] = (name, "ReturnValue")
    # an end point has no gap on one side: use the other
    lens = {}
    for name, own, other, y in (("LenIn", "GapIn", "GapOut", 850), ("LenOut", "GapOut", "GapIn", 950)):
        none = dmath(g, name + "None", "Less_DoubleDouble", gaps[own], None, 1250, y, b_default="0.01", out=BOOL)
        g.call(name, MATHLIB, "SelectFloat", 1500, y,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(gaps[other], (name, "A"))
        g.link(gaps[own], (name, "B"))
        g.link(none, (name, "bPickA"))
        g.call(name + "Tan", MATHLIB, "Multiply_VectorFloat", 1750, y,
               [("A", "in", STRUCT(VECTOR), None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link(("Dir", "ReturnValue"), (name + "Tan", "A"))
        g.link((name, "ReturnValue"), (name + "Tan", "B"))
        lens[name] = (name + "Tan", "ReturnValue")
    g.call("SetTans", SPL, "SetTangentsAtSplinePoint", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None),
            ("PointIndex", "in", INT, None), ("InArriveTangent", "in", STRUCT(VECTOR), None), ("InLeaveTangent", "in", STRUCT(VECTOR), None),
            ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'), ("bUpdateSpline", "in", BOOL, 'DefaultValue="false"')])
    g.link(("ForPts", "LoopBody"), ("SetTans", "execute"))
    g.link(spl, ("SetTans", "self"))
    g.link(i, ("SetTans", "PointIndex"))
    g.link(lens["LenIn"], ("SetTans", "InArriveTangent"))
    g.link(lens["LenOut"], ("SetTans", "InLeaveTangent"))
    return g.render()


def make_course():
    """MakeCourse(Id, Ship, ToHome) -> Course: a new spline component on BP_MapLoad (Loom can't add components),
    filled by BPL_FDVoyage.FillCourse - the course of dock Id's stand-in (see there)."""
    g = Graph()
    F = "MakeCourse"
    ctype, cdefault = CLASSPIN(ACTORCOMP, SPLINE)
    g.node("NewSpline", K2 + "K2Node_AddComponentByClass", [], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("Class", "in", ctype, cdefault), ("bManualAttachment", "in", BOOL, 'DefaultValue="false"'),
            ("RelativeTransform", "in", STRUCT(TRANSFORM), None), ("ReturnValue", "out", OBJ(SPLINE), None)])
    get_local(g, "GetId", F, "Id", INT, 0, 300)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 400)
    get_local(g, "GetToHome", F, "ToHome", BOOL, 0, 500)
    loom_call(g, "Call", VOYAGE_LIB, "FillCourse", 300, 0,
              ins=[("Id", INT), ("Ship", OBJ(SHIP)), ("ToHome", BOOL), ("Course", OBJ(SPLINE))])
    g.link(("NewSpline", "then"), ("Call", "execute"))
    g.link(("GetId", "Id"), ("Call", "Id"))
    g.link(("GetShip", "Ship"), ("Call", "Ship"))
    g.link(("GetToHome", "ToHome"), ("Call", "ToHome"))
    g.link(("NewSpline", "ReturnValue"), ("Call", "Course"))
    return g.render()



SPECS = {
    "MakeCourse": fn_spec(("NewSpline", "execute"), inputs=[("Id", INT), ("Ship", OBJ(SHIP)), ("ToHome", BOOL)],
                          outputs=[("Course", OBJ(SPLINE))],
                          returns=[("Call", "then")], values=[("NewSpline", "ReturnValue", "Course")]),
    "SmoothTangents": fn_spec(("ForPts", "execute"), inputs=[("Spline", OBJ(SPLINE))]),
    "WaitHeading": fn_spec(("HomeDock", "execute"), inputs=[("Id", INT), ("HomeFwd", STRUCT(VECTOR))],
                           outputs=[("Fwd", STRUCT(VECTOR))], returns=[("LookUp", "then_0")],
                           values=[("Turned", "ReturnValue", "Fwd")]),
}


GRAPHS = {
    "MakeCourse": make_course,
    "SmoothTangents": smooth_tangents,
    "WaitHeading": wait_heading,
}
