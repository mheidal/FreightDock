"""Turning a cell path into a sailable course: turn arcs at corners, the waiting heading, smoothed spline
tangents, and MakeCourse, which builds the voyage spline.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import (
    BOOL, CLASSPIN, DOUBLE, EXEC, FLOAT, INT, INT_SET, MAP_INT_INT, MAP_INT_VECTOR, OBJ,
    SPLINE_SPACE, STR, STRUCT, VEC_ARRAY)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, K2, MATHLIB, MODAPI, NDOCK, NDOCKSTATE, SHIP, SPLINE, TRANSFORM,
    VECTOR, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, arr_item, arrfn, bnot, bop, branch, break_struct, break_vec, chain, dmath,
    dmath1, for_loop, get_local, get_member, get_self, ii, make_vec, map_add, map_find, set_contains, set_local,
    set_pin_default, set_self, user_call)
from fdgen.core.text import concat_parts, log_msg, to_str
from fdgen.features.standins import zoomed_child
from fdgen.routes.cells import cell_key_call


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


def turn_arc():
    """TurnArc(Pos, Fwd, Target, Backward) -> Pts, Used: leaving Pos along Fwd, a circle round to where the heading
    points at Target (then straight on). Up to six tries, the first whose points - and the straight from its end to
    Target, sampled every half cell - all stay off Blocked cells (beyond 2 cells from Pos, the berth's own building)
    wins: the shorter turn direction then the other, each at TurnRadius,
    TightTurn1 x and TightTurn2 x it (a ship turns tighter slowly). A try fails too if Target is inside its circle.
    Used is the radius that worked, 0 if none did: no points, and the ship turns in place (VoyageTick). Points are
    every CourseSpacing / 2 along the arc (Pos excluded); Backward lists them in reverse (an arrival: pass the end
    pose with Fwd reversed and the previous point as Target).
    Locals: Arc (Vector array), Hits (Integer), Radius, Side, PrefSide, UsedRadius (Float).
    Wire Done -> Return, GetArcForReturn -> Pts, GetUsedForReturn -> Used."""
    g = Graph()
    F = "TurnArc"
    L = lambda name, var, t, x, y: get_local(g, name, F, var, t, x, y)
    L("GetPos", "Pos", STRUCT(VECTOR), 0, 400)
    L("GetFwd", "Fwd", STRUCT(VECTOR), 0, 500)
    L("GetTarget", "Target", STRUCT(VECTOR), 0, 600)
    L("GetBackward", "Backward", BOOL, 0, 700)
    L("GetArc", "Arc", VEC_ARRAY, 0, 800)
    L("GetHits", "Hits", INT, 0, 900)
    L("GetR", "Radius", DOUBLE, 0, 1000)
    L("GetSide", "Side", DOUBLE, 0, 1100)
    L("GetPref", "PrefSide", DOUBLE, 0, 1200)
    L("GetUsed", "UsedRadius", DOUBLE, 0, 1300)
    get_self(g, "GetBaseR", "TurnRadius", DOUBLE, 0, 1400)
    get_self(g, "GetSpacing", "CourseSpacing", DOUBLE, 0, 1500)
    get_self(g, "GetBlocked", "Blocked", INT_SET, 0, 1600)
    get_self(g, "GetTight1", "TightTurn1", DOUBLE, 0, 1700)
    get_self(g, "GetTight2", "TightTurn2", DOUBLE, 0, 1800)
    get_self(g, "GetCellSize", "CellSize", DOUBLE, 0, 1900)
    arc = ("GetArc", "Arc")
    TWO_PI = "6.283185"

    # heading and its normal in the XY plane
    fwx, fwy, _ = break_vec(g, "FwdXY", ("GetFwd", "Fwd"), 0, 2100)
    g.call("Zero", MATHLIB, "Multiply_DoubleDouble", 0, 2250,
           [("A", "in", DOUBLE, 'DefaultValue="0.0"'), ("B", "in", DOUBLE, 'DefaultValue="0.0"'), ("ReturnValue", "out", DOUBLE, None)])
    g.call("H", MATHLIB, "Normal", 250, 2100, [("A", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(make_vec(g, "Flat", fwx, fwy, ("Zero", "ReturnValue"), 250, 2250), ("H", "A"))
    hx, hy, _ = break_vec(g, "HXY", ("H", "ReturnValue"), 500, 2100)
    px, py, pz = break_vec(g, "PXY", ("GetPos", "Pos"), 500, 2250)
    tx, ty, _ = break_vec(g, "TXY", ("GetTarget", "Target"), 500, 2400)
    nx = dmath(g, "NX", "Multiply_DoubleDouble", hy, None, 750, 2100, b_default="-1.0")
    ny = hx

    def circle(p, s_src, r_src, y0):
        """The circle on side s (+1 / -1) of radius r: centre, angle at Pos, sweep to the tangent point, validity."""
        sr = dmath(g, p + "SR", "Multiply_DoubleDouble", s_src, r_src, 1000, y0)
        cx = dmath(g, p + "CX", "Add_DoubleDouble", px, dmath(g, p + "OX", "Multiply_DoubleDouble", nx, sr, 1250, y0), 1500, y0)
        cy = dmath(g, p + "CY", "Add_DoubleDouble", py, dmath(g, p + "OY", "Multiply_DoubleDouble", ny, sr, 1250, y0 + 100), 1500, y0 + 100)
        vx = dmath(g, p + "VX", "Subtract_DoubleDouble", tx, cx, 1750, y0)
        vy = dmath(g, p + "VY", "Subtract_DoubleDouble", ty, cy, 1750, y0 + 100)
        d2 = dmath(g, p + "D2", "Add_DoubleDouble", dmath(g, p + "VX2", "Multiply_DoubleDouble", vx, vx, 2000, y0),
                   dmath(g, p + "VY2", "Multiply_DoubleDouble", vy, vy, 2000, y0 + 100), 2250, y0)
        d = dmath1(g, p + "D", "Sqrt", d2, 2500, y0)
        valid = dmath(g, p + "Valid", "Greater_DoubleDouble", d,
                      dmath(g, p + "RPlus", "Add_DoubleDouble", r_src, None, 2500, y0 + 100, b_default="1.0"), 2750, y0, out=BOOL)
        phi = dmath(g, p + "Phi", "Atan2", vy, vx, 2000, y0 + 250, pins=("Y", "X"))
        ratio = dmath(g, p + "Ratio", "FMin", dmath(g, p + "RoverD", "Divide_DoubleDouble", r_src,
                                                   dmath(g, p + "DMin", "FMax", d, None, 2500, y0 + 400, b_default="1.0"), 2750, y0 + 400),
                      None, 3000, y0 + 400, b_default="1.0")
        alpha = dmath1(g, p + "Alpha", "Acos", ratio, 3250, y0 + 400)
        theta_q = dmath(g, p + "ThetaQ", "Subtract_DoubleDouble", phi,
                        dmath(g, p + "SAlpha", "Multiply_DoubleDouble", s_src, alpha, 3500, y0 + 400), 3750, y0 + 250)
        theta0 = dmath(g, p + "Theta0", "Atan2", dmath(g, p + "WY", "Subtract_DoubleDouble", py, cy, 2000, y0 + 550),
                       dmath(g, p + "WX", "Subtract_DoubleDouble", px, cx, 2000, y0 + 650), 2250, y0 + 550, pins=("Y", "X"))
        raw = dmath(g, p + "RawSweep", "Multiply_DoubleDouble", s_src,
                    dmath(g, p + "DTheta", "Subtract_DoubleDouble", theta_q, theta0, 4000, y0 + 250), 4250, y0 + 250)
        g.call(p + "Sweep", MATHLIB, "FWrap", 4500, y0 + 250,
               [("Value", "in", DOUBLE, None), ("Min", "in", DOUBLE, 'DefaultValue="0.0"'), ("Max", "in", DOUBLE, f'DefaultValue="{TWO_PI}"'),
                ("ReturnValue", "out", DOUBLE, None)])
        g.link(raw, (p + "Sweep", "Value"))
        return dict(cx=cx, cy=cy, theta0=theta0, sweep=(p + "Sweep", "ReturnValue"), valid=valid)

    # preferred direction: the shorter valid turn at full radius
    g.call("PlusOne", MATHLIB, "Multiply_DoubleDouble", 750, 2500,
           [("A", "in", DOUBLE, 'DefaultValue="1.0"'), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", DOUBLE, None)])
    g.call("MinusOne", MATHLIB, "Multiply_DoubleDouble", 750, 2600,
           [("A", "in", DOUBLE, 'DefaultValue="-1.0"'), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", DOUBLE, None)])
    left = circle("L", ("PlusOne", "ReturnValue"), ("GetBaseR", "TurnRadius"), 2800)
    right = circle("R", ("MinusOne", "ReturnValue"), ("GetBaseR", "TurnRadius"), 3600)
    shorter = dmath(g, "LShorter", "LessEqual_DoubleDouble", left["sweep"], right["sweep"], 5000, 3000, out=BOOL)
    prefer_left = bop(g, "PreferLeft", "BooleanAND", left["valid"],
                      bop(g, "LBetter", "BooleanOR", shorter, bnot(g, "RInvalid", right["valid"], 5250, 3100), 5500, 3000), 5750, 3000)
    g.call("PrefS", MATHLIB, "SelectFloat", 6000, 3000,
           [("A", "in", DOUBLE, 'DefaultValue="1.0"'), ("B", "in", DOUBLE, 'DefaultValue="-1.0"'), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", DOUBLE, None)])
    g.link(prefer_left, ("PrefS", "bPickA"))

    arrfn(g, "ClearArc", "Array_Clear", 0, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None)])
    g.link(arc, ("ClearArc", "TargetArray"))
    set_local(g, "SetPref", F, "PrefSide", DOUBLE, 250, 0)
    g.link(("ClearArc", "then"), ("SetPref", "execute"))
    g.link(("PrefS", "ReturnValue"), ("SetPref", "PrefSide"))
    set_local(g, "NoneUsed", F, "UsedRadius", DOUBLE, 500, 0)
    set_pin_default(g, "NoneUsed", "UsedRadius", "0.0")
    g.link(("SetPref", "then"), ("NoneUsed", "execute"))

    # the tries: k = 0..5 -> radius factor (1, TightTurn1, TightTurn2)[k / 2], side PrefSide or -PrefSide by k % 2
    for_loop(g, "Tries", 750, 0, first=0, last=5, with_break=True)
    g.link(("NoneUsed", "then"), ("Tries", "Exec"))
    k = ("Tries", "Index")
    level = ii(g, "Level", "Divide_IntInt", k, None, 750, 300, b_default="2")
    g.call("Factor12", MATHLIB, "SelectFloat", 1000, 300,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetTight1", "TightTurn1"), ("Factor12", "A"))
    g.link(("GetTight2", "TightTurn2"), ("Factor12", "B"))
    g.link(ii(g, "Level1", "EqualEqual_IntInt", level, None, 1000, 450, b_default="1", out=BOOL), ("Factor12", "bPickA"))
    g.call("Factor", MATHLIB, "SelectFloat", 1250, 300,
           [("A", "in", DOUBLE, 'DefaultValue="1.0"'), ("B", "in", DOUBLE, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Factor12", "ReturnValue"), ("Factor", "B"))
    g.link(ii(g, "Level0", "EqualEqual_IntInt", level, None, 1250, 450, b_default="0", out=BOOL), ("Factor", "bPickA"))
    set_local(g, "SetR", F, "Radius", DOUBLE, 1000, 0)
    g.link(("Tries", "LoopBody"), ("SetR", "execute"))
    g.link(dmath(g, "TryR", "Multiply_DoubleDouble", ("GetBaseR", "TurnRadius"), ("Factor", "ReturnValue"), 1500, 300), ("SetR", "Radius"))
    odd = ii(g, "Odd", "Percent_IntInt", k, None, 1250, 600, b_default="2")
    g.call("SideNow", MATHLIB, "SelectFloat", 1500, 600,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(dmath(g, "OtherSide", "Multiply_DoubleDouble", ("GetPref", "PrefSide"), None, 1250, 750, b_default="-1.0"), ("SideNow", "A"))
    g.link(("GetPref", "PrefSide"), ("SideNow", "B"))
    g.link(ii(g, "IsOdd", "EqualEqual_IntInt", odd, None, 1500, 750, b_default="1", out=BOOL), ("SideNow", "bPickA"))
    set_local(g, "SetSide", F, "Side", DOUBLE, 1250, 0)
    g.link(("SetR", "then"), ("SetSide", "execute"))
    g.link(("SideNow", "ReturnValue"), ("SetSide", "Side"))
    arrfn(g, "ResetArc", "Array_Clear", 1500, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None)])
    g.link(arc, ("ResetArc", "TargetArray"))
    g.link(("SetSide", "then"), ("ResetArc", "execute"))
    set_local(g, "ZeroHits", F, "Hits", INT, 1750, 0)
    set_pin_default(g, "ZeroHits", "Hits", "0")
    g.link(("ResetArc", "then"), ("ZeroHits", "execute"))

    # this try's circle
    cur = circle("C", ("GetSide", "Side"), ("GetR", "Radius"), 4500)
    branch(g, "BrValid", 2000, 0)
    g.link(("ZeroHits", "then"), ("BrValid", "execute"))
    g.link(cur["valid"], ("BrValid", "Condition"))
    step = dmath(g, "Step", "Multiply_DoubleDouble", ("GetSpacing", "CourseSpacing"), None, 2000, 5800, b_default="0.5")
    length = dmath(g, "ArcLen", "Multiply_DoubleDouble", ("GetR", "Radius"), cur["sweep"], 2250, 5800)
    n = dmath1(g, "NPts", "FCeil", dmath(g, "Per", "Divide_DoubleDouble", length, step, 2500, 5800), 2750, 5800, out=INT)
    n = ii(g, "NPts1", "Max", n, None, 3000, 5800, b_default="1")
    for_loop(g, "ForPts", 2250, 0, first=1)
    g.link(n, ("ForPts", "LastIndex"))
    g.link(("BrValid", "then"), ("ForPts", "Exec"))
    g.call("KD", MATHLIB, "Conv_IntToDouble", 2250, 6000, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("ForPts", "Index"), ("KD", "inInt"))
    g.call("ND", MATHLIB, "Conv_IntToDouble", 2500, 6000, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(n, ("ND", "inInt"))
    frac = dmath(g, "Frac", "Divide_DoubleDouble", ("KD", "ReturnValue"), ("ND", "ReturnValue"), 2750, 6000)
    ang = dmath(g, "PAng", "Add_DoubleDouble", cur["theta0"],
                dmath(g, "PTurn", "Multiply_DoubleDouble",
                      dmath(g, "PSSweep", "Multiply_DoubleDouble", ("GetSide", "Side"), cur["sweep"], 3000, 6100), frac, 3250, 6100), 3500, 6100)
    qx = dmath(g, "PQX", "Add_DoubleDouble", cur["cx"],
               dmath(g, "PRCos", "Multiply_DoubleDouble", ("GetR", "Radius"), dmath1(g, "PCos", "Cos", ang, 3750, 6100), 4000, 6100), 4250, 6100)
    qy = dmath(g, "PQY", "Add_DoubleDouble", cur["cy"],
               dmath(g, "PRSin", "Multiply_DoubleDouble", ("GetR", "Radius"), dmath1(g, "PSin", "Sin", ang, 3750, 6250), 4000, 6250), 4250, 6250)
    q = make_vec(g, "PQ", qx, qy, pz, 4500, 6100)
    branch(g, "BrBack", 2500, 0)
    g.link(("ForPts", "LoopBody"), ("BrBack", "execute"))
    g.link(("GetBackward", "Backward"), ("BrBack", "Condition"))
    arrfn(g, "Prepend", "Array_Insert", 2750, -150,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None),
           ("NewItem", "in", STRUCT(VECTOR), None), ("Index", "in", INT, 'DefaultValue="0"')])
    g.link(("BrBack", "then"), ("Prepend", "execute"))
    g.link(arc, ("Prepend", "TargetArray"))
    g.link(q, ("Prepend", "NewItem"))
    arrfn(g, "Append", "Array_Add", 2750, 150,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None),
           ("NewItem", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", INT, None)])
    g.link(("BrBack", "else"), ("Append", "execute"))
    g.link(arc, ("Append", "TargetArray"))
    g.link(q, ("Append", "NewItem"))
    # count points on Blocked cells, outside the berth's own two cells
    hit = set_contains(g, "OnBlocked", ("GetBlocked", "Blocked"), cell_key_call(g, "QKey", q, 4750, 6100), 5000, 6100)
    g.call("FromPos", MATHLIB, "Vector_Distance2D", 4750, 6250,
           [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(q, ("FromPos", "v1"))
    g.link(("GetPos", "Pos"), ("FromPos", "v2"))
    past_berth = dmath(g, "PastBerth", "Greater_DoubleDouble", ("FromPos", "ReturnValue"),
                       dmath(g, "Exempt", "Multiply_DoubleDouble", ("GetCellSize", "CellSize"), None, 5000, 6400, b_default="2.0"),
                       5250, 6250, out=BOOL)
    branch(g, "BrHit", 3000, 0)
    g.link(("Prepend", "then"), ("BrHit", "execute"))
    g.link(("Append", "then"), ("BrHit", "execute"))
    g.link(bop(g, "Clips", "BooleanAND", hit, past_berth, 5500, 6150), ("BrHit", "Condition"))
    set_local(g, "CountHit", F, "Hits", INT, 3250, 0)
    g.link(("BrHit", "then"), ("CountHit", "execute"))
    g.link(ii(g, "HitsPlus", "Add_IntInt", ("GetHits", "Hits"), None, 3250, 300, b_default="1"), ("CountHit", "Hits"))
    # the arc is clean: check the straight from its end to Target too
    end_ang = dmath(g, "EAng", "Add_DoubleDouble", cur["theta0"],
                    dmath(g, "ETurn", "Multiply_DoubleDouble", ("GetSide", "Side"), cur["sweep"], 3000, 6600), 3250, 6600)
    ex = dmath(g, "EX", "Add_DoubleDouble", cur["cx"],
               dmath(g, "ERCos", "Multiply_DoubleDouble", ("GetR", "Radius"), dmath1(g, "ECos", "Cos", end_ang, 3500, 6600), 3750, 6600), 4000, 6600)
    ey = dmath(g, "EY", "Add_DoubleDouble", cur["cy"],
               dmath(g, "ERSin", "Multiply_DoubleDouble", ("GetR", "Radius"), dmath1(g, "ESin", "Sin", end_ang, 3500, 6750), 3750, 6750), 4000, 6750)
    arc_end = make_vec(g, "ArcEnd", ex, ey, pz, 4250, 6600)
    g.call("LegLen", MATHLIB, "Vector_Distance2D", 4500, 6600,
           [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(arc_end, ("LegLen", "v1"))
    g.link(("GetTarget", "Target"), ("LegLen", "v2"))
    half_cell = dmath(g, "HalfCell", "Multiply_DoubleDouble", ("GetCellSize", "CellSize"), None, 4500, 6750, b_default="0.5")
    m = dmath1(g, "LegSteps", "FCeil", dmath(g, "LegPer", "Divide_DoubleDouble", ("LegLen", "ReturnValue"), half_cell, 4750, 6600),
               5000, 6600, out=INT)
    m = ii(g, "LegSteps1", "Max", m, None, 5250, 6600, b_default="1")
    branch(g, "BrArcOk", 2500, -600)
    g.link(("ForPts", "Completed"), ("BrArcOk", "execute"))
    g.link(ii(g, "ArcNoHits", "EqualEqual_IntInt", ("GetHits", "Hits"), None, 2500, -750, b_default="0", out=BOOL), ("BrArcOk", "Condition"))
    for_loop(g, "ForLeg", 2750, -600, first=1)
    g.link(ii(g, "LegLast", "Subtract_IntInt", m, None, 2750, -750, b_default="1"), ("ForLeg", "LastIndex"))
    g.link(("BrArcOk", "then"), ("ForLeg", "Exec"))
    g.call("LJ", MATHLIB, "Conv_IntToDouble", 3000, -750, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("ForLeg", "Index"), ("LJ", "inInt"))
    g.call("LM", MATHLIB, "Conv_IntToDouble", 3000, -850, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(m, ("LM", "inInt"))
    g.call("LegPt", MATHLIB, "VLerp", 3250, -750,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("Alpha", "in", FLOAT, None),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(arc_end, ("LegPt", "A"))
    g.link(("GetTarget", "Target"), ("LegPt", "B"))
    g.link(dmath(g, "LegAlpha", "Divide_DoubleDouble", ("LJ", "ReturnValue"), ("LM", "ReturnValue"), 3250, -900), ("LegPt", "Alpha"))
    leg_hit = set_contains(g, "LegBlocked", ("GetBlocked", "Blocked"), cell_key_call(g, "LegKey", ("LegPt", "ReturnValue"), 3500, -750), 3750, -750)
    g.call("LegFromPos", MATHLIB, "Vector_Distance2D", 3500, -900,
           [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("LegPt", "ReturnValue"), ("LegFromPos", "v1"))
    g.link(("GetPos", "Pos"), ("LegFromPos", "v2"))
    leg_past = dmath(g, "LegPastBerth", "Greater_DoubleDouble", ("LegFromPos", "ReturnValue"), ("Exempt", "ReturnValue"), 3750, -900, out=BOOL)
    branch(g, "BrLegHit", 3000, -600)
    g.link(("ForLeg", "LoopBody"), ("BrLegHit", "execute"))
    g.link(bop(g, "LegClips", "BooleanAND", leg_hit, leg_past, 4000, -800), ("BrLegHit", "Condition"))
    set_local(g, "CountLegHit", F, "Hits", INT, 3250, -600)
    g.link(("BrLegHit", "then"), ("CountLegHit", "execute"))
    g.link(("HitsPlus", "ReturnValue"), ("CountLegHit", "Hits"))
    # a clean arc and straight: keep it and stop trying
    branch(g, "BrClean", 2500, -300)
    g.link(("ForLeg", "Completed"), ("BrClean", "execute"))
    g.link(("BrArcOk", "else"), ("BrClean", "execute"))
    g.link(ii(g, "NoHits", "EqualEqual_IntInt", ("GetHits", "Hits"), None, 2500, -450, b_default="0", out=BOOL), ("BrClean", "Condition"))
    set_local(g, "KeepR", F, "UsedRadius", DOUBLE, 2750, -300)
    g.link(("BrClean", "then"), ("KeepR", "execute"))
    g.link(("GetR", "Radius"), ("KeepR", "UsedRadius"))
    g.link(("KeepR", "then"), ("Tries", "Break"))

    # after the tries: nothing clean -> no points
    used_none = dmath(g, "UsedNone", "LessEqual_DoubleDouble", ("GetUsed", "UsedRadius"), None, 1000, -450, b_default="0.0", out=BOOL)
    branch(g, "BrNone", 1000, -300)
    g.link(("Tries", "Completed"), ("BrNone", "execute"))
    g.link(used_none, ("BrNone", "Condition"))
    arrfn(g, "DropArc", "Array_Clear", 1250, -300,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None)])
    g.link(arc, ("DropArc", "TargetArray"))
    g.link(("BrNone", "then"), ("DropArc", "execute"))
    g.node("Done", K2 + "K2Node_ExecutionSequence", [], 1500, -300, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
    g.link(("BrNone", "else"), ("Done", "execute"))
    g.link(("DropArc", "then"), ("Done", "execute"))
    get_local(g, "GetArcForReturn", F, "Arc", VEC_ARRAY, 1750, -450)
    get_local(g, "GetUsedForReturn", F, "UsedRadius", DOUBLE, 1750, -350)
    return g.render()


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
    """MakeCourse(Id, Ship, ToHome) -> Course: a new spline for dock Id's stand-in. It runs from a start pose to an
    end pose - the home berth (position and berthed ship's heading) and the target's stand-off point (WaitHeading),
    swapped when homeward - through the planned route's points between them (or straight when there is no route).
    It leaves the start pose and reaches the end pose along TurnArc circles, so the heading never jumps; each turn
    is aimed at the farthest route point in straight sight of its pose (at least 2 x TurnRadius away, so the turns
    have room), skipping the points before it. Tangents are set by SmoothTangents. Where a turn would clip land there is no
    arc: the course runs straight from / to the pose and the ship turns in place (VoyageTick, using the end heading
    saved in VoyageEndFwd). Resampled every CourseSpacing with corners rounded (corner_leg).
    If a turn finds no clean arc and straight to that point, nearer points are tried in turn (down to the nearest
    2 x TurnRadius away) before turning in place. The route's first point, the home berth's stand-off point, isn't
    aimed at (it is beside the berthed ship, too near to turn towards); where the home end turns in place, the course
    runs via it.
    Locals: Raw, Mid, ArcOut, ArcIn (Vector arrays), CourseSpline (Spline Component), StartIdx, EndIdx, Anchor, OutFloor,
    InCeil, TryFrom (Integer), UsedOut, UsedIn (Float).
    Wire Finish -> Return and GetCourseForReturn -> Course."""
    g = Graph()
    F = "MakeCourse"
    L = lambda name, var, t, x, y: get_local(g, name, F, var, t, x, y)
    L("GetId", "Id", INT, 0, 600)
    L("GetShip", "Ship", OBJ(SHIP), 0, 700)
    L("GetToHome", "ToHome", BOOL, 0, 800)
    L("GetRaw", "Raw", VEC_ARRAY, 0, 900)
    L("GetCourse", "CourseSpline", OBJ(SPLINE), 0, 1000)
    L("GetMid", "Mid", VEC_ARRAY, 0, 1100)
    L("GetStartIdx", "StartIdx", INT, 0, 1200)
    L("GetEndIdx", "EndIdx", INT, 0, 1300)
    get_self(g, "GetRoutePts", "RoutePts", MAP_INT_VECTOR, 0, 1400)
    get_self(g, "GetRouteLen", "RouteLen", MAP_INT_INT, 0, 1500)
    get_self(g, "GetVTarget", "VoyageTarget", MAP_INT_VECTOR, 0, 1600)
    get_self(g, "GetSpacing", "CourseSpacing", DOUBLE, 0, 1700)
    get_self(g, "GetRadius", "TurnRadius", DOUBLE, 0, 1800)
    key, raw, to_home, mid = ("GetId", "Id"), ("GetRaw", "Raw"), ("GetToHome", "ToHome"), ("GetMid", "Mid")
    course = ("GetCourse", "CourseSpline")
    SPL = f"/Script/CoreUObject.Class'{SPLINE}'"

    def vsel(name, a_src, b_src, cond, x, y):
        g.call(name, MATHLIB, "SelectVector", x, y,
               [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("bPickA", "in", BOOL, None),
                ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link(a_src, (name, "A"))
        g.link(b_src, (name, "B"))
        g.link(cond, (name, "bPickA"))
        return (name, "ReturnValue")

    # the berthed ship's (hidden) zoomed-in model: berth position and heading (its bow is the actor's right vector)
    _, child = zoomed_child(g, "Z", ("GetShip", "Ship"), 250, 1900)
    home = actor_loc(g, "HomePos", child, 750, 1900)
    g.call("Fwd", f"/Script/CoreUObject.Class'{ACTOR}'", "GetActorRightVector", 750, 2050,
           [("self", "in", OBJ(ACTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(child, ("Fwd", "self"))
    _, _, home_z = break_vec(g, "HomeXYZ", home, 1000, 1900)

    def at_home_z(name, src, x, y):
        sx, sy, _ = break_vec(g, name + "XYZ", src, x, y)
        return make_vec(g, name, sx, sy, home_z, x + 250, y)

    def add_to(name, arr, src, x, y):
        arrfn(g, name, "Array_Add", x, y,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None),
               ("NewItem", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", INT, None)])
        g.link(arr, (name, "TargetArray"))
        g.link(src, (name, "NewItem"))

    # the two poses
    map_find(g, "N", ("GetRouteLen", "RouteLen"), key, MAP_INT_INT, INT, 250, 2300, key_type=INT)
    has_route = ii(g, "HasRoute", "Greater_IntInt", ("N", "Value"), None, 500, 2300, b_default="1", out=BOOL)
    base = ii(g, "Base", "Multiply_IntInt", key, None, 250, 2450, b_default="1000")
    last_pt = ii(g, "LastPt", "Subtract_IntInt", ("N", "Value"), None, 250, 2600, b_default="1")
    last_slot = ii(g, "LastSlot", "Add_IntInt", base, last_pt, 500, 2450)
    map_find(g, "RouteEnd", ("GetRoutePts", "RoutePts"), last_slot, MAP_INT_VECTOR, STRUCT(VECTOR), 750, 2450, key_type=INT)
    map_find(g, "Target", ("GetVTarget", "VoyageTarget"), key, MAP_INT_VECTOR, STRUCT(VECTOR), 750, 2600, key_type=INT)
    away = at_home_z("AwayPos", vsel("AwayRaw", ("RouteEnd", "Value"), ("Target", "Value"), has_route, 1000, 2450), 1250, 2450)
    user_call(g, "Wait", "WaitHeading", 500, 0, ins=[("Id", INT), ("HomeFwd", STRUCT(VECTOR))], outs=[("Fwd", STRUCT(VECTOR))])
    g.link(key, ("Wait", "Id"))
    g.link(("Fwd", "ReturnValue"), ("Wait", "HomeFwd"))
    start_pos = vsel("StartPos", away, home, to_home, 1750, 2300)
    start_fwd = vsel("StartFwd", ("Wait", "Fwd"), ("Fwd", "ReturnValue"), to_home, 1750, 2450)
    end_pos = vsel("EndPos", home, away, to_home, 1750, 2600)
    end_fwd = vsel("EndFwd", ("Fwd", "ReturnValue"), ("Wait", "Fwd"), to_home, 1750, 2750)

    # Mid: the route points between the two ends - the route minus its last point (the target's stand-off point, an
    # end pose) and its first (the home berth's stand-off point: beside the berthed ship, too near to turn towards);
    # reversed when homeward. The home stand-off point is only used when the home end turns in place (below).
    for n_, arr, x in (("ClearRaw", raw, 0), ("ClearMid", mid, 250)):
        arrfn(g, n_, "Array_Clear", x, 0,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None)])
        g.link(arr, (n_, "TargetArray"))
    chain(g, "ClearRaw", "ClearMid", "Wait")
    last_mid = ii(g, "LastMid", "Subtract_IntInt", ("N", "Value"), None, 750, 300, b_default="2")
    for_loop(g, "ForMid", 750, 0, first=1)
    g.link(last_mid, ("ForMid", "LastIndex"))
    g.link(("Wait", "then"), ("ForMid", "Exec"))
    rev = ii(g, "RevIdx", "Subtract_IntInt", last_pt, ("ForMid", "Index"), 1000, 300)
    g.call("Idx", MATHLIB, "SelectInt", 1250, 300,
           [("A", "in", INT, None), ("B", "in", INT, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", INT, None)])
    g.link(rev, ("Idx", "A"))
    g.link(("ForMid", "Index"), ("Idx", "B"))
    g.link(to_home, ("Idx", "bPickA"))
    slot = ii(g, "Slot", "Add_IntInt", base, ("Idx", "ReturnValue"), 1500, 300)
    map_find(g, "RoutePt", ("GetRoutePts", "RoutePts"), slot, MAP_INT_VECTOR, STRUCT(VECTOR), 1750, 300, key_type=INT)
    add_to("AddMid", mid, at_home_z("MidAtZ", ("RoutePt", "Value"), 2000, 300), 1000, 0)
    g.link(("ForMid", "LoopBody"), ("AddMid", "execute"))

    # StartIdx / EndIdx: the first / last Mid point at least 2 x TurnRadius from the start / end
    arrfn(g, "MidLen", "Array_Length", 1250, 600, [("TargetArray", "in", VEC_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(mid, ("MidLen", "TargetArray"))
    last_i = ii(g, "LastI", "Subtract_IntInt", ("MidLen", "ReturnValue"), None, 1500, 600, b_default="1")
    room = dmath(g, "Room", "Multiply_DoubleDouble", ("GetRadius", "TurnRadius"), None, 1500, 750, b_default="2.0")
    set_local(g, "InitStart", F, "StartIdx", INT, 1250, -200)
    g.link(last_i, ("InitStart", "StartIdx"))
    set_local(g, "InitEnd", F, "EndIdx", INT, 1500, -200)
    set_pin_default(g, "InitEnd", "EndIdx", "0")
    g.link(("ForMid", "Completed"), ("InitStart", "execute"))
    g.link(("InitStart", "then"), ("InitEnd", "execute"))

    def first_far(p, pos_src, from_end, after, x):
        for_loop(g, p + "Scan", x, 0, first=0, with_break=True)
        g.link(last_i, (p + "Scan", "LastIndex"))
        g.link(after, (p + "Scan", "Exec"))
        idx = ii(g, p + "J", "Subtract_IntInt", last_i, (p + "Scan", "Index"), x, 900) if from_end else (p + "Scan", "Index")
        pt = arr_item(g, p + "Pt", mid, idx, STRUCT(VECTOR), x + 250, 900)
        g.call(p + "Dist", MATHLIB, "Vector_Distance2D", x + 500, 900,
               [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(pos_src, (p + "Dist", "v1"))
        g.link(pt, (p + "Dist", "v2"))
        far = dmath(g, p + "Far", "GreaterEqual_DoubleDouble", (p + "Dist", "ReturnValue"), room, x + 750, 900, out=BOOL)
        branch(g, p + "BrFar", x + 250, 0)
        g.link((p + "Scan", "LoopBody"), (p + "BrFar", "execute"))
        g.link(far, (p + "BrFar", "Condition"))
        var = "EndIdx" if from_end else "StartIdx"
        set_local(g, p + "Set", F, var, INT, x + 500, 0)
        g.link((p + "BrFar", "then"), (p + "Set", "execute"))
        g.link(idx, (p + "Set", var))
        g.link((p + "Set", "then"), (p + "Scan", "Break"))
        return (p + "Scan", "Completed")

    done_start = first_far("S", start_pos, False, ("InitEnd", "then"), 1750)
    done_end = first_far("E", end_pos, True, done_start, 2750)
    set_local(g, "FixEnd", F, "EndIdx", INT, 3750, 0)
    g.link(done_end, ("FixEnd", "execute"))
    g.link(ii(g, "EndAtLeast", "Max", ("GetEndIdx", "EndIdx"), ("GetStartIdx", "StartIdx"), 3750, 300), ("FixEnd", "EndIdx"))

    # aim each turn at the farthest route point in straight sight of its pose (ClearLine, which exempts the docks'
    # surroundings via PlanStart / PlanGoal), so the course turns straight onto the long leg
    has_mid = ii(g, "HasMid", "Greater_IntInt", ("MidLen", "ReturnValue"), None, 4000, 600, b_default="0", out=BOOL)
    set_self(g, "SetPlanStart", "PlanStart", STRUCT(VECTOR), 3800, -300)
    g.link(start_pos, ("SetPlanStart", "PlanStart"))
    set_self(g, "SetPlanGoal", "PlanGoal", STRUCT(VECTOR), 3900, -300)
    g.link(end_pos, ("SetPlanGoal", "PlanGoal"))
    set_local(g, "SetOutFloor", F, "OutFloor", INT, 3750, -150)
    g.link(("FixEnd", "then"), ("SetOutFloor", "execute"))
    g.link(("GetStartIdx", "StartIdx"), ("SetOutFloor", "OutFloor"))
    set_local(g, "SetInCeil", F, "InCeil", INT, 3750, -300)
    g.link(("SetOutFloor", "then"), ("SetInCeil", "execute"))
    g.link(("GetEndIdx", "EndIdx"), ("SetInCeil", "InCeil"))
    g.link(("SetInCeil", "then"), ("SetPlanStart", "execute"))
    g.link(("SetPlanStart", "then"), ("SetPlanGoal", "execute"))
    branch(g, "BrSight", 3950, -300)
    g.link(("SetPlanGoal", "then"), ("BrSight", "execute"))
    g.link(has_mid, ("BrSight", "Condition"))

    def in_sight(p, pos_src, mid_idx, x):
        user_call(g, p + "Clear", "ClearLine", x + 250, -300, ins=[("A", STRUCT(VECTOR)), ("B", STRUCT(VECTOR))], outs=[("LineClear", BOOL)])
        g.link(pos_src, (p + "Clear", "A"))
        g.link(arr_item(g, p + "Pt", mid, mid_idx, STRUCT(VECTOR), x + 250, -100), (p + "Clear", "B"))
        branch(g, p + "BrSeen", x + 500, -300)
        g.link((p + "Clear", "then"), (p + "BrSeen", "execute"))
        g.link((p + "Clear", "LineClear"), (p + "BrSeen", "Condition"))
        return p + "Clear", p + "BrSeen"

    # forward from StartIdx (absolute indices; LastIndex = EndIdx doesn't change here)
    for_loop(g, "FwdSight", 4000, -500, with_break=True)
    g.link(ii(g, "FwdFrom", "Add_IntInt", ("GetStartIdx", "StartIdx"), None, 4000, -650, b_default="1"), ("FwdSight", "FirstIndex"))
    g.link(("GetEndIdx", "EndIdx"), ("FwdSight", "LastIndex"))
    g.link(("BrSight", "then"), ("FwdSight", "Exec"))
    clear_f, seen_f = in_sight("F", start_pos, ("FwdSight", "Index"), 4000)
    g.link(("FwdSight", "LoopBody"), (clear_f, "execute"))
    set_local(g, "FSet", F, "StartIdx", INT, 4750, -400)
    g.link((seen_f, "then"), ("FSet", "execute"))
    g.link(("FwdSight", "Index"), ("FSet", "StartIdx"))
    g.link((seen_f, "else"), ("FwdSight", "Break"))
    # backward from EndIdx (counted down from a copy, Anchor, as EndIdx moves)
    set_local(g, "SetAnchor", F, "Anchor", INT, 5000, -500)
    g.link(("GetEndIdx", "EndIdx"), ("SetAnchor", "Anchor"))
    g.link(("FwdSight", "Completed"), ("SetAnchor", "execute"))
    L("GetAnchor", "Anchor", INT, 5000, -650)
    for_loop(g, "BackSight", 5250, -500, first=1, with_break=True)
    g.link(ii(g, "BackCount", "Subtract_IntInt", ("GetAnchor", "Anchor"), ("GetStartIdx", "StartIdx"), 5250, -650), ("BackSight", "LastIndex"))
    g.link(("SetAnchor", "then"), ("BackSight", "Exec"))
    back_idx = ii(g, "BackIdx", "Subtract_IntInt", ("GetAnchor", "Anchor"), ("BackSight", "Index"), 5250, -800)
    clear_b, seen_b = in_sight("B", end_pos, back_idx, 5250)
    g.link(("BackSight", "LoopBody"), (clear_b, "execute"))
    set_local(g, "BSet", F, "EndIdx", INT, 6000, -400)
    g.link((seen_b, "then"), ("BSet", "execute"))
    g.link(back_idx, ("BSet", "EndIdx"))
    g.link((seen_b, "else"), ("BackSight", "Break"))
    g.node("SightDone", K2 + "K2Node_ExecutionSequence", [], 6250, -500, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
    g.link(("BackSight", "Completed"), ("SightDone", "execute"))
    g.link(("BrSight", "else"), ("SightDone", "execute"))

    # the turns: try the chosen route point, then each one nearer the pose (down to the nearest 2 x TurnRadius away)
    # until TurnArc finds a clean arc and straight; if none does, that end turns in place and keeps all its points
    L("GetOutFloor", "OutFloor", INT, 4000, 1100)
    L("GetInCeil", "InCeil", INT, 4000, 1200)
    L("GetTryFrom", "TryFrom", INT, 4000, 1300)
    L("GetUsedOut", "UsedOut", DOUBLE, 4000, 1400)
    L("GetUsedIn", "UsedIn", DOUBLE, 4000, 1500)
    g.call("Back", MATHLIB, "Multiply_VectorFloat", 4500, 900,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", DOUBLE, 'DefaultValue="-1.0"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(end_fwd, ("Back", "A"))

    def turn(name, pos, fwd, other_pose, backward, arc_var, idx_var, limit_src, outward, used_var, fallback, after, x):
        set_local(g, name + "From", F, "TryFrom", INT, x, 0)
        g.link(after, (name + "From", "execute"))
        g.link(("Get" + idx_var, idx_var), (name + "From", "TryFrom"))
        set_local(g, name + "NoUse", F, used_var, DOUBLE, x + 125, 0)
        set_pin_default(g, name + "NoUse", used_var, "0.0")
        g.link((name + "From", "then"), (name + "NoUse", "execute"))
        # how many candidates: |TryFrom - limit|, none without route points
        span = ii(g, name + "Span", "Subtract_IntInt", *((("GetTryFrom", "TryFrom"), limit_src) if outward else (limit_src, ("GetTryFrom", "TryFrom"))),
                  x, 300)
        g.call(name + "Count", MATHLIB, "SelectInt", x + 250, 300,
               [("A", "in", INT, None), ("B", "in", INT, 'DefaultValue="0"'), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", INT, None)])
        g.link(ii(g, name + "Span0", "Max", span, None, x + 125, 450, b_default="0"), (name + "Count", "A"))
        g.link(has_mid, (name + "Count", "bPickA"))
        for_loop(g, name + "Tries", x + 250, 0, first=0, with_break=True)
        g.link((name + "Count", "ReturnValue"), (name + "Tries", "LastIndex"))
        g.link((name + "NoUse", "then"), (name + "Tries", "Exec"))
        cand = ii(g, name + "Cand", "Subtract_IntInt" if outward else "Add_IntInt", ("GetTryFrom", "TryFrom"), (name + "Tries", "Index"), x + 250, 600)
        target = vsel(name + "Target", arr_item(g, name + "Pt", mid, cand, STRUCT(VECTOR), x + 500, 600), other_pose, has_mid, x + 750, 600)
        user_call(g, name, "TurnArc", x + 500, 0,
                  ins=[("Pos", STRUCT(VECTOR)), ("Fwd", STRUCT(VECTOR)), ("Target", STRUCT(VECTOR)), ("Backward", BOOL)],
                  outs=[("Pts", VEC_ARRAY), ("Used", DOUBLE)])
        for pin, src in (("Pos", pos), ("Fwd", fwd), ("Target", target)):
            g.link(src, (name, pin))
        set_pin_default(g, name, "Backward", backward)
        g.link((name + "Tries", "LoopBody"), (name, "execute"))
        branch(g, name + "BrOk", x + 750, 0)
        g.link((name, "then"), (name + "BrOk", "execute"))
        g.link(dmath(g, name + "Ok", "Greater_DoubleDouble", (name, "Used"), None, x + 750, 300, b_default="0.0", out=BOOL), (name + "BrOk", "Condition"))
        set_local(g, name + "Keep", F, arc_var, VEC_ARRAY, x + 1000, 0)
        g.link((name + "BrOk", "then"), (name + "Keep", "execute"))
        g.link((name, "Pts"), (name + "Keep", arc_var))
        set_local(g, name + "Aim", F, idx_var, INT, x + 1250, 0)
        g.link((name + "Keep", "then"), (name + "Aim", "execute"))
        g.link(cand, (name + "Aim", idx_var))
        set_local(g, name + "Used", F, used_var, DOUBLE, x + 1500, 0)
        g.link((name + "Aim", "then"), (name + "Used", "execute"))
        g.link((name, "Used"), (name + "Used", used_var))
        g.link((name + "Used", "then"), (name + "Tries", "Break"))
        # none worked: no arc, and every route point at this end is kept
        branch(g, name + "BrNone", x + 500, -300)
        g.link((name + "Tries", "Completed"), (name + "BrNone", "execute"))
        g.link(dmath(g, name + "None", "LessEqual_DoubleDouble", ("Get" + used_var, used_var), None, x + 500, -450, b_default="0.0", out=BOOL),
               (name + "BrNone", "Condition"))
        arrfn(g, name + "NoArc", "Array_Clear", x + 750, -300,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None)])
        L(name + "GetArc", arc_var, VEC_ARRAY, x + 750, -450)
        g.link((name + "GetArc", arc_var), (name + "NoArc", "TargetArray"))
        g.link((name + "BrNone", "then"), (name + "NoArc", "execute"))
        set_local(g, name + "Widen", F, idx_var, INT, x + 1000, -300)
        g.link((name + "NoArc", "then"), (name + "Widen", "execute"))
        if isinstance(fallback, str):
            set_pin_default(g, name + "Widen", idx_var, fallback)
        else:
            g.link(fallback, (name + "Widen", idx_var))
        g.node(name + "Next", K2 + "K2Node_ExecutionSequence", [], x + 1250, -300,
               [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
        g.link((name + "Widen", "then"), (name + "Next", "execute"))
        g.link((name + "BrNone", "else"), (name + "Next", "execute"))
        return (name + "Next", "then_0")

    after_out = turn("TurnOut", start_pos, start_fwd, end_pos, "false", "ArcOut", "StartIdx", ("GetOutFloor", "OutFloor"), True,
                     "UsedOut", "0", ("SightDone", "then_0"), 4000)
    after_in = turn("TurnIn", end_pos, ("Back", "ReturnValue"), start_pos, "true", "ArcIn", "EndIdx", ("GetInCeil", "InCeil"), False,
                    "UsedIn", last_i, after_out, 5750)

    # Raw: start, turn out, Mid[StartIdx..EndIdx], turn in, end
    def append(name, src_var, x):
        arrfn(g, name, "Array_Append", x, 0,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", VEC_ARRAY, None),
               ("SourceArray", "in", VEC_ARRAY, None)])
        g.link(raw, (name, "TargetArray"))
        L("Get" + src_var, src_var, VEC_ARRAY, x, 300)
        g.link(("Get" + src_var, src_var), (name, "SourceArray"))

    # where the home end turns in place, the course runs via the home stand-off point (checked clear by the planner)
    map_find(g, "HomeStandOff", ("GetRoutePts", "RoutePts"), base, MAP_INT_VECTOR, STRUCT(VECTOR), 6000, 1900, key_type=INT)
    stand_off = at_home_z("StandOffAtZ", ("HomeStandOff", "Value"), 6250, 1900)

    def via_stand_off(name, used_var, homeward, x):
        L("Get" + name + used_var, used_var, DOUBLE, x, 2050)
        pivot = dmath(g, name + "Pivot", "LessEqual_DoubleDouble", ("Get" + name + used_var, used_var), None, x, 2200,
                      b_default="0.0", out=BOOL)
        way = to_home if homeward else bnot(g, name + "Outward", to_home, x, 2350)
        cond = bop(g, name + "Cond", "BooleanAND", bop(g, name + "Way", "BooleanAND", pivot, way, x + 250, 2200),
                   has_route, x + 500, 2200)
        branch(g, name + "Br", x, 0)
        g.link(cond, (name + "Br", "Condition"))
        add_to(name, raw, stand_off, x + 250, 0)
        g.link((name + "Br", "then"), (name, "execute"))
        g.node(name + "Next", K2 + "K2Node_ExecutionSequence", [], x + 500, 0,
               [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
        g.link((name + "Br", "else"), (name + "Next", "execute"))
        g.link((name, "then"), (name + "Next", "execute"))
        return (name + "Next", "then_0")

    add_to("AddStart", raw, start_pos, 6000, 0)
    g.link(after_in, ("AddStart", "execute"))
    append("AddOut", "ArcOut", 6250)
    g.link(("AddStart", "then"), ("AddOut", "execute"))
    after_out_pts = via_stand_off("StandOffOut", "UsedOut", False, 6250)
    g.link(("AddOut", "then"), ("StandOffOutBr", "execute"))
    branch(g, "BrMid", 6500, 0)
    g.link(after_out_pts, ("BrMid", "execute"))
    g.link(has_mid, ("BrMid", "Condition"))
    for_loop(g, "ForKeep", 6750, 0)
    g.link(("GetStartIdx", "StartIdx"), ("ForKeep", "FirstIndex"))
    g.link(("GetEndIdx", "EndIdx"), ("ForKeep", "LastIndex"))
    g.link(("BrMid", "then"), ("ForKeep", "Exec"))
    add_to("AddKeep", raw, arr_item(g, "KeepPt", mid, ("ForKeep", "Index"), STRUCT(VECTOR), 7000, 300), 7000, 0)
    g.link(("ForKeep", "LoopBody"), ("AddKeep", "execute"))
    append("AddIn", "ArcIn", 7250)
    g.link(("ForKeep", "Completed"), ("AddIn", "execute"))
    g.link(("BrMid", "else"), ("AddIn", "execute"))
    after_in_pts = via_stand_off("StandOffIn", "UsedIn", True, 7250)
    g.link(("AddIn", "then"), ("StandOffInBr", "execute"))
    add_to("AddEnd", raw, end_pos, 7500, 0)
    g.link(after_in_pts, ("AddEnd", "execute"))
    # the heading to turn to at the end (VoyageTick)
    get_self(g, "GetEndFwds", "VoyageEndFwd", MAP_INT_VECTOR, 7750, 300)
    map_add(g, "SaveEndFwd", ("GetEndFwds", "VoyageEndFwd"), key, end_fwd, MAP_INT_VECTOR, STRUCT(VECTOR), 7750, 0, key_type=INT)
    g.link(("AddEnd", "then"), ("SaveEndFwd", "execute"))
    # log how each end turns: "arc r=..." or "turn in place"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 7750, 1100)

    def how(p, used, x):
        g.call(p + "Pivot", MATHLIB, "LessEqual_DoubleDouble", x, 1300,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="0.0"'), ("ReturnValue", "out", BOOL, None)])
        g.link(used, (p + "Pivot", "A"))
        arc_txt = concat_parts(g, p + "ArcTxt", ["arc r=", to_str(g, p + "R", "Conv_IntToString", "InInt", INT,
                                                                       dmath1(g, p + "RInt", "Round", used, x, 1450, out=INT), x + 250, 1450)],
                               x, 1600)
        g.call(p + "How", MATHLIB, "SelectString", x + 500, 1300,
               [("A", "in", STR, 'DefaultValue="turn in place"'), ("B", "in", STR, None), ("bPickA", "in", BOOL, None),
                ("ReturnValue", "out", STR, None)])
        g.link((arc_txt, "ReturnValue"), (p + "How", "B"))
        g.link((p + "Pivot", "ReturnValue"), (p + "How", "bPickA"))
        return (p + "How", "ReturnValue")

    g.call("Dir", MATHLIB, "SelectString", 8000, 1100,
           [("A", "in", STR, 'DefaultValue="home"'), ("B", "in", STR, 'DefaultValue="out"'), ("bPickA", "in", BOOL, None),
            ("ReturnValue", "out", STR, None)])
    g.link(to_home, ("Dir", "bPickA"))
    msg = concat_parts(g, "CourseMsg", ["Course for dock ", to_str(g, "SDock", "Conv_IntToString", "InInt", INT, key, 8000, 1250),
                                        " (", ("Dir", "ReturnValue"), "): departure ", how("Out", ("GetUsedOut", "UsedOut"), 8250),
                                        " to point ", to_str(g, "SStart", "Conv_IntToString", "InInt", INT, ("GetStartIdx", "StartIdx"), 8750, 1250),
                                        ", arrival ", how("In", ("GetUsedIn", "UsedIn"), 9000),
                                        " from point ", to_str(g, "SEnd", "Conv_IntToString", "InInt", INT, ("GetEndIdx", "EndIdx"), 9500, 1250),
                                        " of ", to_str(g, "SMid", "Conv_IntToString", "InInt", INT, ("MidLen", "ReturnValue"), 9750, 1250)],
                       8000, 1800)
    log_msg(g, "LogCourse", "GetModAPI", 7875, 0)
    g.link(("SaveEndFwd", "then"), ("LogCourse", "execute"))
    g.link((msg, "ReturnValue"), ("LogCourse", "Msg"))

    # the spline: first raw point, then each leg cut into CourseSpacing steps
    ctype, cdefault = CLASSPIN(ACTORCOMP, SPLINE)
    g.node("NewSpline", K2 + "K2Node_AddComponentByClass", [], 8000, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("Class", "in", ctype, cdefault), ("bManualAttachment", "in", BOOL, 'DefaultValue="false"'),
            ("RelativeTransform", "in", STRUCT(TRANSFORM), None), ("ReturnValue", "out", OBJ(SPLINE), None)])
    g.link(("LogCourse", "then"), ("NewSpline", "execute"))
    set_local(g, "SetCourse", F, "CourseSpline", OBJ(SPLINE), 2250, 0)
    g.link(("NewSpline", "then"), ("SetCourse", "execute"))
    g.link(("NewSpline", "ReturnValue"), ("SetCourse", "CourseSpline"))
    g.call("ClearPts", SPL, "ClearSplinePoints", 2500, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None),
            ("bUpdateSpline", "in", BOOL, 'DefaultValue="false"')])
    g.link(("SetCourse", "then"), ("ClearPts", "execute"))
    g.link(course, ("ClearPts", "self"))

    def add_point(name, pos_src, x, y):
        g.call(name, SPL, "AddSplinePoint", x, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None),
                ("position", "in", STRUCT(VECTOR), None), ("CoordinateSpace", "in", SPLINE_SPACE, 'DefaultValue="World"'),
                ("bUpdateSpline", "in", BOOL, 'DefaultValue="false"')])
        g.link(course, (name, "self"))
        g.link(pos_src, (name, "position"))

    g.node("Raw0", K2 + "K2Node_GetArrayItem", [], 2750, 300,
           [("Array", "in", VEC_ARRAY, None), ("Dimension 1", "in", INT, 'DefaultValue="0"'), ("Output", "out", STRUCT(VECTOR), None)])
    g.link(raw, ("Raw0", "Array"))
    add_point("PtFirst", ("Raw0", "Output"), 2750, 0)
    g.link(("ClearPts", "then"), ("PtFirst", "execute"))
    arrfn(g, "RawLen", "Array_Length", 3000, 300, [("TargetArray", "in", VEC_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(raw, ("RawLen", "TargetArray"))
    last_leg = ii(g, "LastLeg", "Subtract_IntInt", ("RawLen", "ReturnValue"), None, 3250, 300, b_default="2")
    for_loop(g, "ForLegs", 3000, 0, first=0)
    g.link(last_leg, ("ForLegs", "LastIndex"))
    g.link(("PtFirst", "then"), ("ForLegs", "Exec"))
    a = arr_item(g, "LegA", raw, ("ForLegs", "Index"), STRUCT(VECTOR), 3250, 450)
    nxt = ii(g, "NextIdx", "Add_IntInt", ("ForLegs", "Index"), None, 3250, 600, b_default="1")
    b = arr_item(g, "LegB", raw, nxt, STRUCT(VECTOR), 3500, 600)
    get_self(g, "GetCorner", "CornerRadius", DOUBLE, 3000, 1100)
    corner_leg(g, a, b, ("ForLegs", "Index"), last_leg, ("GetSpacing", "CourseSpacing"), ("GetCorner", "CornerRadius"),
               ("ForLegs", "LoopBody"), add_point, 3250, 900)

    g.call("Finish", SPL, "UpdateSpline", 4000, -200,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(SPLINE), None)])
    user_call(g, "Smooth", "SmoothTangents", 0, -450, ins=[("Spline", OBJ(SPLINE))])
    g.link(("ForLegs", "Completed"), ("Smooth", "execute"))
    g.link(course, ("Smooth", "Spline"))
    g.link(("Smooth", "then"), ("Finish", "execute"))
    g.link(course, ("Finish", "self"))
    L("GetCourseForReturn", "CourseSpline", OBJ(SPLINE), 4250, -350)
    return g.render()


SPECS = {
    "MakeCourse": fn_spec(("ClearRaw", "execute"), inputs=[("Id", INT), ("Ship", OBJ(SHIP)), ("ToHome", BOOL)],
                          outputs=[("Course", OBJ(SPLINE))],
                          locals_=[("Raw", VEC_ARRAY), ("CourseSpline", OBJ(SPLINE)), ("Mid", VEC_ARRAY),
                                   ("StartIdx", INT), ("EndIdx", INT), ("ArcOut", VEC_ARRAY), ("ArcIn", VEC_ARRAY),
                                   ("Anchor", INT), ("OutFloor", INT), ("InCeil", INT), ("TryFrom", INT), ("UsedOut", DOUBLE),
                                   ("UsedIn", DOUBLE)],
                          returns=[("Finish", "then")], values=[("GetCourseForReturn", "CourseSpline", "Course")]),
    "SmoothTangents": fn_spec(("ForPts", "execute"), inputs=[("Spline", OBJ(SPLINE))]),
    "TurnArc": fn_spec(("ClearArc", "execute"),
                       inputs=[("Pos", STRUCT(VECTOR)), ("Fwd", STRUCT(VECTOR)), ("Target", STRUCT(VECTOR)), ("Backward", BOOL)],
                       outputs=[("Pts", VEC_ARRAY), ("Used", DOUBLE)],
                       locals_=[("Arc", VEC_ARRAY), ("Hits", INT), ("Radius", DOUBLE), ("Side", DOUBLE), ("PrefSide", DOUBLE),
                                ("UsedRadius", DOUBLE)],
                       returns=[("Done", "then_0")],
                       values=[("GetArcForReturn", "Arc", "Pts"), ("GetUsedForReturn", "UsedRadius", "Used")]),
    "WaitHeading": fn_spec(("HomeDock", "execute"), inputs=[("Id", INT), ("HomeFwd", STRUCT(VECTOR))],
                           outputs=[("Fwd", STRUCT(VECTOR))], returns=[("LookUp", "then_0")],
                           values=[("Turned", "ReturnValue", "Fwd")]),
}


GRAPHS = {
    "MakeCourse": make_course,
    "TurnArc": turn_arc,
    "SmoothTangents": smooth_tangents,
    "WaitHeading": wait_heading,
}
