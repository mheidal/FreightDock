"""Route map cells: a cell is 100 units (2 game tiles). Cell keys and positions, blocked / penalty bookkeeping,
line-of-sight over cells (ClearLine), the stand-off point off a dock, and the octile distance.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, DOUBLE, INT, MAP_INT_INT, OBJ, STRUCT
from fdgen.core.paths import MAPLIB, MATHLIB, VECTOR, VOYAGE_LIB, WORKDOCK
from fdgen.core.nodes import (
    bop, branch, get_local, get_self, ii, loom_call, map_add,
    user_call)
from fdgen.core.specs import fn_spec


# Route cells are CellSize (100) units square. A cell key packs its grid coordinates into one int:
#   key = (floor(x / CellSize) + 2048) * 4096 + (floor(y / CellSize) + 2048)
# so the neighbour at (dx, dy) is key + dx * 4096 + dy.
KEY_OFF = 2048


KEY_MUL = 4096


def cell_key_call(g, name, pos_src, x, y):
    user_call(g, name, "CellKey", x, y, ins=[("Pos", STRUCT(VECTOR))], outs=[("Key", INT)], impure=False)
    g.link(pos_src, (name, "Pos"))
    return (name, "Key")


def cell_pos_call(g, name, key_src, x, y):
    user_call(g, name, "CellPos", x, y, ins=[("Key", INT)], outs=[("Pos", STRUCT(VECTOR))], impure=False)
    g.link(key_src, (name, "Key"))
    return (name, "Pos")


def near_end(g, p, pos_src, x, y):
    """True when pos is within (ClearanceCells + 2) cells of PlanStart or PlanGoal: the docks' approaches, where the
    clearance around the shore is ignored so a ship can leave and reach its berth."""
    get_self(g, p + "Clear", "ClearanceCells", INT, x, y)
    get_self(g, p + "Size", "CellSize", DOUBLE, x, y + 100)
    get_self(g, p + "S", "PlanStart", STRUCT(VECTOR), x, y + 200)
    get_self(g, p + "G", "PlanGoal", STRUCT(VECTOR), x, y + 300)
    r = ii(g, p + "Cells", "Add_IntInt", (p + "Clear", "ClearanceCells"), None, x + 250, y, b_default="2")
    g.call(p + "CellsD", MATHLIB, "Conv_IntToDouble", x + 500, y, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(r, (p + "CellsD", "inInt"))
    g.call(p + "Radius", MATHLIB, "Multiply_DoubleDouble", x + 750, y,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link((p + "CellsD", "ReturnValue"), (p + "Radius", "A"))
    g.link((p + "Size", "CellSize"), (p + "Radius", "B"))
    near = []
    for end in ("S", "G"):
        g.call(p + "D" + end, MATHLIB, "Vector_Distance2D", x + 250, y + 200 + (100 if end == "G" else 0),
               [("v1", "in", STRUCT(VECTOR), None), ("v2", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(pos_src, (p + "D" + end, "v1"))
        g.link((p + end, "Plan" + ("Start" if end == "S" else "Goal")), (p + "D" + end, "v2"))
        g.call(p + "In" + end, MATHLIB, "Less_DoubleDouble", x + 500, y + 200 + (100 if end == "G" else 0),
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", BOOL, None)])
        g.link((p + "D" + end, "ReturnValue"), (p + "In" + end, "A"))
        g.link((p + "Radius", "ReturnValue"), (p + "In" + end, "B"))
        near.append((p + "In" + end, "ReturnValue"))
    return bop(g, p + "Near", "BooleanOR", near[0], near[1], x + 1000, y + 250)


def add_penalty(g, p, pen_src, key_src, value_src, after, x, y):
    """Penalty[key] = max(Penalty[key], value). Returns the node whose "then" continues (both branches join there)."""
    g.call(p + "Old", MAPLIB, "Map_Find", x, y + 200,
           [("TargetMap", "in", MAP_INT_INT, None), ("Key", "in", INT, None), ("Value", "out", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(pen_src, (p + "Old", "TargetMap"))
    g.link(key_src, (p + "Old", "Key"))
    g.call(p + "Higher", MATHLIB, "Greater_IntInt", x + 250, y + 200,
           [("A", "in", INT, None), ("B", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(value_src, (p + "Higher", "A"))
    g.link((p + "Old", "Value"), (p + "Higher", "B"))
    branch(g, p + "Br", x, y)
    g.link(after, (p + "Br", "execute"))
    g.link((p + "Higher", "ReturnValue"), (p + "Br", "Condition"))
    map_add(g, p + "Set", pen_src, key_src, value_src, MAP_INT_INT, INT, x + 250, y, key_type=INT)
    g.link((p + "Br", "then"), (p + "Set", "execute"))


def cell_key():
    """Pure CellKey(Pos) -> Key. Wire Key (node "Key") to the Return node."""
    g = Graph()
    get_local(g, "GetPos", "CellKey", "Pos", STRUCT(VECTOR), 0, 0)
    get_self(g, "GetSize", "CellSize", DOUBLE, 0, 200)
    g.call("XY", MATHLIB, "BreakVector", 250, 0,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None), ("Z", "out", DOUBLE, None)])
    g.link(("GetPos", "Pos"), ("XY", "InVec"))
    parts = []
    for i, axis in enumerate(("X", "Y")):
        y = 300 * i
        g.call(f"Div{axis}", MATHLIB, "Divide_DoubleDouble", 500, y,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(("XY", axis), (f"Div{axis}", "A"))
        g.link(("GetSize", "CellSize"), (f"Div{axis}", "B"))
        g.call(f"Floor{axis}", MATHLIB, "FFloor", 750, y, [("A", "in", DOUBLE, None), ("ReturnValue", "out", INT, None)])
        g.link((f"Div{axis}", "ReturnValue"), (f"Floor{axis}", "A"))
        parts.append(ii(g, f"Off{axis}", "Add_IntInt", (f"Floor{axis}", "ReturnValue"), None, 1000, y, b_default=KEY_OFF))
    hi = ii(g, "Hi", "Multiply_IntInt", parts[0], None, 1250, 0, b_default=KEY_MUL)
    ii(g, "Key", "Add_IntInt", hi, parts[1], 1500, 0)
    return g.render()


def cell_pos():
    """Pure CellPos(Key) -> Pos: the cell's centre at Z = 0. Wire node "Pos" to the Return node."""
    g = Graph()
    get_local(g, "GetKey", "CellPos", "Key", INT, 0, 0)
    get_self(g, "GetSize", "CellSize", DOUBLE, 0, 300)
    coords = []
    for i, (axis, func) in enumerate((("X", "Divide_IntInt"), ("Y", "Percent_IntInt"))):
        y = 200 * i
        c = ii(g, f"Grid{axis}", func, ("GetKey", "Key"), None, 250, y, b_default=KEY_MUL)
        c = ii(g, f"Cell{axis}", "Subtract_IntInt", c, None, 500, y, b_default=KEY_OFF)
        g.call(f"Dbl{axis}", MATHLIB, "Conv_IntToDouble", 750, y, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(c, (f"Dbl{axis}", "inInt"))
        g.call(f"Mid{axis}", MATHLIB, "Add_DoubleDouble", 1000, y,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="0.5"'), ("ReturnValue", "out", DOUBLE, None)])
        g.link((f"Dbl{axis}", "ReturnValue"), (f"Mid{axis}", "A"))
        g.call(f"World{axis}", MATHLIB, "Multiply_DoubleDouble", 1250, y,
               [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
        g.link((f"Mid{axis}", "ReturnValue"), (f"World{axis}", "A"))
        g.link(("GetSize", "CellSize"), (f"World{axis}", "B"))
        coords.append((f"World{axis}", "ReturnValue"))
    g.call("Pos", MATHLIB, "MakeVector", 1500, 0,
           [("X", "in", DOUBLE, None), ("Y", "in", DOUBLE, None), ("Z", "in", DOUBLE, 'DefaultValue="0.0"'),
            ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(coords[0], ("Pos", "X"))
    g.link(coords[1], ("Pos", "Y"))
    return g.render()


def clear_line():
    """ClearLine(A, B) -> LineClear: BPL_FDVoyage.ClearLine - no blocked cell, other dock's outline or (away from the
    ends) near-shore cell anywhere the segment touches (an exact walk along the grid, so no corner is cut)."""
    g = Graph()
    get_local(g, "GetA", "ClearLine", "A", STRUCT(VECTOR), 0, 250)
    get_local(g, "GetB", "ClearLine", "B", STRUCT(VECTOR), 0, 350)
    loom_call(g, "Call", VOYAGE_LIB, "ClearLine", 250, 0, ins=[("A", STRUCT(VECTOR)), ("B", STRUCT(VECTOR))],
              outs=[("ReturnValue", BOOL)])
    g.link(("GetA", "A"), ("Call", "A"))
    g.link(("GetB", "B"), ("Call", "B"))
    return g.render()


def stand_off_point():
    """StandOffPoint(Dock) -> Pos: BPL_FDVoyage.StandOffPoint - StandOff units out from the dock's berth, at Z = 0,
    turned up to 80 degrees where the way straight out is blocked."""
    g = Graph()
    get_local(g, "GetDock", "StandOffPoint", "Dock", OBJ(WORKDOCK), 0, 250)
    loom_call(g, "Call", VOYAGE_LIB, "StandOffPoint", 250, 0, ins=[("Dock", OBJ(WORKDOCK))],
              outs=[("ReturnValue", STRUCT(VECTOR))])
    g.link(("GetDock", "Dock"), ("Call", "Dock"))
    return g.render()


def octile(g, p, key_src, goal_src, x, y):
    """A* heuristic in cost units (10 per straight step, 14 per diagonal)."""
    d = []
    for axis, func in (("X", "Divide_IntInt"), ("Y", "Percent_IntInt")):
        a = ii(g, f"{p}A{axis}", func, key_src, None, x, y, b_default=KEY_MUL)
        b = ii(g, f"{p}B{axis}", func, goal_src, None, x, y + 100, b_default=KEY_MUL)
        diff = ii(g, f"{p}D{axis}", "Subtract_IntInt", a, b, x + 250, y)
        g.call(f"{p}Abs{axis}", MATHLIB, "Abs_Int", x + 500, y, [("A", "in", INT, None), ("ReturnValue", "out", INT, None)])
        g.link(diff, (f"{p}Abs{axis}", "A"))
        d.append((f"{p}Abs{axis}", "ReturnValue"))
        y += 200
    mx = ii(g, f"{p}Max", "Max", d[0], d[1], x + 750, y - 400)
    mn = ii(g, f"{p}Min", "Min", d[0], d[1], x + 750, y - 300)
    mx = ii(g, f"{p}Max10", "Multiply_IntInt", mx, None, x + 1000, y - 400, b_default="10")
    mn = ii(g, f"{p}Min4", "Multiply_IntInt", mn, None, x + 1000, y - 300, b_default="4")
    return ii(g, f"{p}H", "Add_IntInt", mx, mn, x + 1250, y - 400)


SPECS = {
    "StandOffPoint": fn_spec(("Call", "execute"), inputs=[("Dock", OBJ(WORKDOCK))], outputs=[("Pos", STRUCT(VECTOR))],
                             returns=[("Call", "then")], values=[("Call", "ReturnValue", "Pos")]),
    "ClearLine": fn_spec(("Call", "execute"), inputs=[("A", STRUCT(VECTOR)), ("B", STRUCT(VECTOR))],
                         outputs=[("LineClear", BOOL)], returns=[("Call", "then")],
                         values=[("Call", "ReturnValue", "LineClear")]),
}


GRAPHS = {
    "CellKey": cell_key,
    "CellPos": cell_pos,
    "ClearLine": clear_line,
    "StandOffPoint": stand_off_point,
}
