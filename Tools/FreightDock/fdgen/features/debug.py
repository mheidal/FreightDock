"""Logging and debug views: Stamp (log time prefix), ship / link / plan / nautical-dock logs, DebugSetup, and the
F7 cell overlay (DebugCells: blocked, penalty and land cells).
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import (
    BOOL, CLASSPIN, DOUBLE, EXEC, INT, INT_ARRAY, INT_SET, KEY, MAP_INT_INT, MAP_NAME_TO,
    NAME, NAME_ARRAY, OBJ, STR, STRUCT, T, TEXT, struct_obj)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, CARGO, FOREACH, GRIDACTOR, ISMC, K2, LINKER, MAPLIB, MATHLIB, MATLIB,
    MID, MODAPI, NDOCK, NDOCKSTATE, PC, PLAYPAWN, ROTATOR, ROUTE_LINE_MAT, ROUTE_STRIP, SETLIB, SHIP, SHIPSTATE,
    STATICS, STRLIB, SYSLIB, TEXTLIB, TRANSFORM, VECTOR, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, all_actors, all_ships, bnot, branch, break_struct, break_vec, comp_owner,
    display_name, dmath, for_each, for_loop, get_local, get_member, get_self, ii, is_valid, make_vec, self_call,
    set_contains, set_local, set_self)
from fdgen.core.text import LOG_PREFIX, fmt_to_string, int_text, log_msg
from fdgen.routes.cells import KEY_MUL, cell_key_call, cell_pos_call


def cargo_to_string():
    g = Graph()
    CARGO = "/Script/NauticalKit.NauticalCargo"
    ITEM = "/Script/NauticalKit.NauticalCargoItem"
    S = "CargoToString"

    g.node("BreakCargo", "/Script/BlueprintGraph.K2Node_BreakStruct",
           [f"StructType={struct_obj(CARGO)}"], 0, 0,
           [("NauticalCargo", "in", STRUCT(CARGO), None),
            ("Items", "out", MAP_NAME_TO(ITEM), None)])
    g.call("Keys", MAPLIB, "Map_Keys", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", MAP_NAME_TO(ITEM), None),
            ("Keys", "out", NAME_ARRAY, None)])
    g.node("ForEach", "/Script/BlueprintGraph.K2Node_MacroInstance", [FOREACH], 500, -50,
           [("Exec", "in", EXEC, None),
            ("Array", "in", NAME_ARRAY, None),
            ("LoopBody", "out", EXEC, None),
            ("Array Element", "out", NAME, None),
            ("Array Index", "out", INT, None),
            ("Completed", "out", EXEC, None)])
    g.call("Find", MAPLIB, "Map_Find", 800, 150,
           [("TargetMap", "in", MAP_NAME_TO(ITEM), None),
            ("Key", "in", NAME, None),
            ("Value", "out", STRUCT(ITEM), None),
            ("ReturnValue", "out", BOOL, None)])
    g.node("BreakItem", "/Script/BlueprintGraph.K2Node_BreakStruct",
           [f"StructType={struct_obj(ITEM)}"], 1050, 150,
           [("NauticalCargoItem", "in", STRUCT(ITEM), None),
            ("ItemName", "out", NAME, None),
            ("Quantity", "out", DOUBLE, None)])
    g.node("Fmt", "/Script/BlueprintGraph.K2Node_FormatText",
           ['PinNames(0)="name"', 'PinNames(1)="qty"'], 1300, 50,
           [("Format", "in", TEXT, 'DefaultTextValue=INVTEXT("{name}={qty}; ")'),
            ("Result", "out", TEXT, None),
            ("name", "in", NAME, None),
            ("qty", "in", DOUBLE, None)])
    g.call("ToStr", TEXTLIB, "Conv_TextToString", 1550, 50,
           [("InText", "in", TEXT, None), ("ReturnValue", "out", STR, None)])
    g.node("GetOut1", "/Script/BlueprintGraph.K2Node_VariableGet", [local_var(S, "Out")], 1550, -50,
           [("Out", "out", STR, None)])
    g.call("Append", STRLIB, "Concat_StrStr", 1800, 0,
           [("A", "in", STR, None), ("B", "in", STR, None), ("ReturnValue", "out", STR, None)])
    g.node("SetOut", "/Script/BlueprintGraph.K2Node_VariableSet", [local_var(S, "Out")], 2050, -50,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Out", "in", STR, None), ("Output_Get", "out", STR, None)])
    g.node("GetOut2", "/Script/BlueprintGraph.K2Node_VariableGet", [local_var(S, "Out")], 800, -200,
           [("Out", "out", STR, None)])

    g.link(("BreakCargo", "Items"), ("Keys", "TargetMap"))
    g.link(("BreakCargo", "Items"), ("Find", "TargetMap"))
    g.link(("Keys", "Keys"), ("ForEach", "Array"))
    g.link(("Keys", "then"), ("ForEach", "Exec"))
    g.link(("ForEach", "Array Element"), ("Find", "Key"))
    g.link(("ForEach", "Array Element"), ("Fmt", "name"))
    g.link(("Find", "Value"), ("BreakItem", "NauticalCargoItem"))
    g.link(("BreakItem", "Quantity"), ("Fmt", "qty"))
    g.link(("Fmt", "Result"), ("ToStr", "InText"))
    g.link(("GetOut1", "Out"), ("Append", "A"))
    g.link(("ToStr", "ReturnValue"), ("Append", "B"))
    g.link(("Append", "ReturnValue"), ("SetOut", "Out"))
    g.link(("ForEach", "LoopBody"), ("SetOut", "execute"))
    return g.render()


def stamp():
    """Pure: "[yyyy-mm-dd hh:mm:ss] [FreightDock] " (LOG_PREFIX) for log lines."""
    g = Graph()
    g.call("Now", MATHLIB, "Now", 0, 0, [("ReturnValue", "out", STRUCT("/Script/CoreUObject.DateTime"), None)])
    g.call("Parts", MATHLIB, "BreakDateTime", 250, 0,
           [("InDateTime", "in", STRUCT("/Script/CoreUObject.DateTime"), None),
            ("Year", "out", INT, None), ("Month", "out", INT, None), ("Day", "out", INT, None),
            ("Hour", "out", INT, None), ("Minute", "out", INT, None), ("Second", "out", INT, None),
            ("Millisecond", "out", INT, None)])
    g.link(("Now", "ReturnValue"), ("Parts", "InDateTime"))
    fields = (("y", "Year", 4), ("mo", "Month", 2), ("d", "Day", 2), ("h", "Hour", 2), ("mi", "Minute", 2), ("s", "Second", 2))
    g.node("Fmt", K2 + "K2Node_FormatText", [f'PinNames({i})="{a}"' for i, (a, _, _) in enumerate(fields)], 750, 0,
           [("Format", "in", TEXT, 'DefaultTextValue=INVTEXT("[{y}-{mo}-{d} {h}:{mi}:{s}] ' + LOG_PREFIX + '")'), ("Result", "out", TEXT, None)]
           + [(a, "in", TEXT, None) for a, _, _ in fields])
    for i, (a, part, digits) in enumerate(fields):
        conv = int_text(g, "T_" + a, 500, 120 * i, digits)
        g.link(("Parts", part), (conv, "Value"))
        g.link((conv, "ReturnValue"), ("Fmt", a))
    g.call("Str", TEXTLIB, "Conv_TextToString", 1000, 0,
           [("InText", "in", TEXT, None), ("ReturnValue", "out", STR, None)])
    g.link(("Fmt", "Result"), ("Str", "InText"))
    # exec pass-through, so the install spec can wire entry -> Pass -> return
    g.node("Pass", K2 + "K2Node_ExecutionSequence", [], 1000, -200,
           [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
    return g.render()


def log_ships():
    g = Graph()
    all_ships(g, "GetAll", 0, 0)
    for_each(g, "ForEach", OBJ(SHIP), 300, 0)
    g.link(("GetAll", "then"), ("ForEach", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForEach", "Array"))

    get_member(g, "GetState", SHIP, "State", STRUCT(SHIPSTATE), 300, 250)
    g.link(("ForEach", "Array Element"), ("GetState", "self"))
    break_struct(g, "BreakState", SHIPSTATE,
                 [("shipName", STR), ("dockedDock", OBJ(NDOCK)), ("worldLoc", STRUCT(VECTOR)), ("cargo", STRUCT(CARGO))],
                 550, 250)
    g.link(("GetState", "State"), ("BreakState", "NauticalShipState"))

    display_name(g, "ActorName", SHIP, 600, 100)
    g.link(("ForEach", "Array Element"), ("ActorName", "Object"))
    display_name(g, "DockName", NDOCK, 850, 300)
    g.link(("BreakState", "dockedDock"), ("DockName", "Object"))
    g.call("LocStr", STRLIB, "Conv_VectorToString", 850, 400,
           [("InVec", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STR, None)])
    g.link(("BreakState", "worldLoc"), ("LocStr", "InVec"))
    g.node("CargoStr", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="CargoToString",bSelfContext=True)'],
           850, 500, [("Cargo", "in", STRUCT(CARGO), None), ("Result", "out", STR, None)])
    g.link(("BreakState", "cargo"), ("CargoStr", "Cargo"))

    s = fmt_to_string(g, "Fmt", "Ship {i} [{actor}] '{name}' docked: {dock} at {loc} | cargo: {cargo}",
                      [("i", INT), ("actor", STR), ("name", STR), ("dock", STR), ("loc", STR), ("cargo", STR)],
                      1150, 100)
    for arg, src in (("i", ("ForEach", "Array Index")), ("actor", ("ActorName", "ReturnValue")),
                     ("name", ("BreakState", "shipName")), ("dock", ("DockName", "ReturnValue")),
                     ("loc", ("LocStr", "ReturnValue")), ("cargo", ("CargoStr", "Result"))):
        g.link(src, ("Fmt", arg))

    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 1400, -100)
    log_msg(g, "Log", "GetModAPI", 1650, 0)
    g.link(("ForEach", "LoopBody"), ("Log", "execute"))
    g.link((s, "ReturnValue"), ("Log", "Msg"))
    return g.render()


def ids_to_string():
    g = Graph()
    F = "IdsToString"
    g.call("ToArray", SETLIB, "Set_ToArray", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("A", "in", INT_SET, None), ("Result", "out", INT_ARRAY, None)])
    for_each(g, "ForIds", INT, 300, 0)
    g.link(("ToArray", "then"), ("ForIds", "Exec"))
    g.link(("ToArray", "Result"), ("ForIds", "Array"))

    set_local(g, "ResetName", F, "Name", STR, 600, 0)
    g.link(("ForIds", "LoopBody"), ("ResetName", "execute"))
    all_actors(g, "GetBuildings", GRIDACTOR, 850, 0)
    g.link(("ResetName", "then"), ("GetBuildings", "execute"))
    for_each(g, "ForBuildings", OBJ(GRIDACTOR), 1150, 0)
    g.link(("GetBuildings", "then"), ("ForBuildings", "Exec"))
    g.link(("GetBuildings", "OutActors"), ("ForBuildings", "Array"))

    get_member(g, "BuildingId", GRIDACTOR, "ID", INT, 1150, 250)
    g.link(("ForBuildings", "Array Element"), ("BuildingId", "self"))
    g.call("IdMatch", MATHLIB, "EqualEqual_IntInt", 1400, 250,
           [("A", "in", INT, None), ("B", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("BuildingId", "ID"), ("IdMatch", "A"))
    g.link(("ForIds", "Array Element"), ("IdMatch", "B"))
    branch(g, "BrMatch", 1650, 0)
    g.link(("ForBuildings", "LoopBody"), ("BrMatch", "execute"))
    g.link(("IdMatch", "ReturnValue"), ("BrMatch", "Condition"))
    display_name(g, "BuildingName", GRIDACTOR, 1650, 250)
    g.link(("ForBuildings", "Array Element"), ("BuildingName", "Object"))
    set_local(g, "SetName", F, "Name", STR, 1900, 0)
    g.link(("BrMatch", "then"), ("SetName", "execute"))
    g.link(("BuildingName", "ReturnValue"), ("SetName", "Name"))

    get_local(g, "GetName", F, "Name", STR, 1400, -250)
    s = fmt_to_string(g, "FmtId", "{id}={name}; ", [("id", INT), ("name", STR)], 1650, -250)
    g.link(("ForIds", "Array Element"), ("FmtId", "id"))
    g.link(("GetName", "Name"), ("FmtId", "name"))
    get_local(g, "GetOut", F, "Out", STR, 1900, -350)
    g.call("Append", STRLIB, "Concat_StrStr", 2150, -250,
           [("A", "in", STR, None), ("B", "in", STR, None), ("ReturnValue", "out", STR, None)])
    g.link(("GetOut", "Out"), ("Append", "A"))
    g.link((s, "ReturnValue"), ("Append", "B"))
    set_local(g, "SetOut", F, "Out", STR, 2400, -250)
    g.link(("ForBuildings", "Completed"), ("SetOut", "execute"))
    g.link(("Append", "ReturnValue"), ("SetOut", "Out"))
    get_local(g, "GetOutForReturn", F, "Out", STR, 600, -250)
    return g.render()


def log_links():
    g = Graph()
    F = "LogLinks"
    get_self(g, "GetDocks", "Docks", OBJ(WORKDOCK, "Array"), 0, 150)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 600)
    for_each(g, "ForDocks", OBJ(WORKDOCK), 250, 0)
    g.link(("GetDocks", "Docks"), ("ForDocks", "Array"))

    comp_owner(g, "Owner", WORKDOCK, 250, 300)
    g.link(("ForDocks", "Array Element"), ("Owner", "self"))
    ctype, cdefault = CLASSPIN(ACTORCOMP, LINKER)
    g.call("FindLinker", f"/Script/CoreUObject.Class'{ACTOR}'", "GetComponentByClass", 500, 300,
           [("self", "in", OBJ(ACTOR), None), ("ComponentClass", "in", ctype, cdefault),
            ("ReturnValue", "out", OBJ(LINKER), None)])
    g.link(("Owner", "ReturnValue"), ("FindLinker", "self"))
    set_local(g, "SetLinker", F, "Linker", OBJ(LINKER), 550, 0)
    g.link(("ForDocks", "LoopBody"), ("SetLinker", "execute"))
    g.link(("FindLinker", "ReturnValue"), ("SetLinker", "Linker"))

    get_local(g, "GetLinker", F, "Linker", OBJ(LINKER), 550, 450)
    is_valid(g, "LinkerValid", LINKER, 800, 200)
    g.link(("GetLinker", "Linker"), ("LinkerValid", "Object"))
    branch(g, "BrLinker", 800, 0)
    g.link(("SetLinker", "then"), ("BrLinker", "execute"))
    g.link(("LinkerValid", "ReturnValue"), ("BrLinker", "Condition"))

    # shared parts of both log lines
    display_name(g, "OwnerName", ACTOR, 500, 500)
    g.link(("Owner", "ReturnValue"), ("OwnerName", "Object"))
    get_member(g, "TargetId", WORKDOCK, "activeTradePartnerId", INT, 500, 650)
    g.link(("ForDocks", "Array Element"), ("TargetId", "self"))

    # linker found: resolve both id sets
    get_member(g, "SrcIds", LINKER, "m_sourceStockpileIds", INT_SET, 1050, 300)
    g.link(("GetLinker", "Linker"), ("SrcIds", "self"))
    self_call(g, "SrcToStr", "IdsToString", 1050, 0,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
               ("Ids", "in", INT_SET, None), ("Result", "out", STR, None)])
    g.link(("BrLinker", "then"), ("SrcToStr", "execute"))
    g.link(("SrcIds", "m_sourceStockpileIds"), ("SrcToStr", "Ids"))
    set_local(g, "SetSrc", F, "Src", STR, 1300, 0)
    g.link(("SrcToStr", "then"), ("SetSrc", "execute"))
    g.link(("SrcToStr", "Result"), ("SetSrc", "Src"))

    get_member(g, "DstIds", LINKER, "m_destStockpileIds", INT_SET, 1550, 300)
    g.link(("GetLinker", "Linker"), ("DstIds", "self"))
    self_call(g, "DstToStr", "IdsToString", 1550, 0,
              [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
               ("Ids", "in", INT_SET, None), ("Result", "out", STR, None)])
    g.link(("SetSrc", "then"), ("DstToStr", "execute"))
    g.link(("DstIds", "m_destStockpileIds"), ("DstToStr", "Ids"))
    set_local(g, "SetDst", F, "Dst", STR, 1800, 0)
    g.link(("DstToStr", "then"), ("SetDst", "execute"))
    g.link(("DstToStr", "Result"), ("SetDst", "Dst"))

    get_local(g, "GetSrc", F, "Src", STR, 1800, 300)
    get_local(g, "GetDst", F, "Dst", STR, 1800, 400)
    s = fmt_to_string(g, "FmtLinks", "Dock {i} [{owner}] targetId: {p} | pick up from: {src} | deliver to: {dst}",
                      [("i", INT), ("owner", STR), ("p", INT), ("src", STR), ("dst", STR)], 2050, 250)
    for arg, src in (("i", ("ForDocks", "Array Index")), ("owner", ("OwnerName", "ReturnValue")),
                     ("p", ("TargetId", "activeTradePartnerId")), ("src", ("GetSrc", "Src")),
                     ("dst", ("GetDst", "Dst"))):
        g.link(src, ("FmtLinks", arg))
    log_msg(g, "LogLinksLine", "GetModAPI", 2550, 0)
    g.link(("SetDst", "then"), ("LogLinksLine", "execute"))
    g.link((s, "ReturnValue"), ("LogLinksLine", "Msg"))

    # no linker
    s2 = fmt_to_string(g, "FmtNoLinker", "Dock {i} [{owner}] targetId: {p} | no StockpileLinker component",
                       [("i", INT), ("owner", STR), ("p", INT)], 1050, 550)
    g.link(("ForDocks", "Array Index"), ("FmtNoLinker", "i"))
    g.link(("OwnerName", "ReturnValue"), ("FmtNoLinker", "owner"))
    g.link(("TargetId", "activeTradePartnerId"), ("FmtNoLinker", "p"))
    log_msg(g, "LogNoLinker", "GetModAPI", 1550, 550)
    g.link(("BrLinker", "else"), ("LogNoLinker", "execute"))
    g.link((s2, "ReturnValue"), ("LogNoLinker", "Msg"))
    return g.render()


CELLS_KEY = "F7"


def debug_cells():
    """DebugCells (every tick while debugging; not called in release - add it to PairKeyTick): CELLS_KEY toggles an overlay of the water map around the camera's
    focal point - land cells (LandNext) in LandCellColor, other Blocked cells (buildings) in BlockedCellColor,
    near-shore (Penalty) cells in PenaltyCellColor - as flat squares (SM_RouteStrip instances), CellsRadius cells each
    way, redrawn once a second.
    Locals: Centre, Key (Integer), Layer (Instanced Static Mesh Component)."""
    g = Graph()
    F = "DebugCells"
    get_self(g, "GetShow", "ShowCells", BOOL, 0, 400)
    get_self(g, "GetNext", "NextCellsDraw", DOUBLE, 0, 500)
    get_self(g, "GetBlockedLayer", "BlockedLayer", OBJ(ISMC), 0, 600)
    get_self(g, "GetPenaltyLayer", "PenaltyLayer", OBJ(ISMC), 0, 700)
    get_self(g, "GetLandLayer", "LandLayer", OBJ(ISMC), 0, 750)
    get_self(g, "GetLand", "LandNext", INT_SET, 0, 1050)
    get_self(g, "GetRadius", "CellsRadius", INT, 0, 800)
    get_self(g, "GetBlocked", "Blocked", INT_SET, 0, 900)
    get_self(g, "GetPenalty", "Penalty", MAP_INT_INT, 0, 1000)
    get_self(g, "GetHeight", "RouteLineHeight", DOUBLE, 0, 1100)
    get_local(g, "GetCentre", F, "Centre", INT, 0, 1200)
    ISM_C = f"/Script/CoreUObject.Class'{ISMC}'"

    # the key: toggle; off -> clear both layers
    g.call("PC", STATICS, "GetPlayerController", 0, 1400,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ(PC), None)])
    g.call("Toggled", f"/Script/CoreUObject.Class'{PC}'", "WasInputKeyJustPressed", 250, 1400,
           [("self", "in", OBJ(PC), None), ("Key", "in", KEY, f'DefaultValue="{CELLS_KEY}"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("PC", "ReturnValue"), ("Toggled", "self"))
    branch(g, "BrToggled", 0, 0)
    g.link(("Toggled", "ReturnValue"), ("BrToggled", "Condition"))
    set_self(g, "Flip", "ShowCells", BOOL, 250, -150)
    g.link(("BrToggled", "then"), ("Flip", "execute"))
    g.link(bnot(g, "NotShown", ("GetShow", "ShowCells"), 250, -300), ("Flip", "ShowCells"))
    set_self(g, "DrawNow", "NextCellsDraw", DOUBLE, 500, -150, literal="0.0")
    g.link(("Flip", "then"), ("DrawNow", "execute"))

    def clear_layer(name, layer, x, y):
        is_valid(g, name + "Ok", ISMC, x, y + 150)
        g.link(layer, (name + "Ok", "Object"))
        branch(g, name + "Br", x, y)
        g.link((name + "Ok", "ReturnValue"), (name + "Br", "Condition"))
        g.call(name, ISM_C, "ClearInstances", x + 250, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ISMC), None)])
        g.link((name + "Br", "then"), (name, "execute"))
        g.link(layer, (name, "self"))
        g.node(name + "Done", K2 + "K2Node_ExecutionSequence", [], x + 500, y, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
        g.link((name, "then"), (name + "Done", "execute"))
        g.link((name + "Br", "else"), (name + "Done", "execute"))
        return (name + "Br", "execute"), (name + "Done", "then_0")

    # on and due?
    branch(g, "BrShow", 750, 0)
    g.link(("DrawNow", "then"), ("BrShow", "execute"))
    g.link(("BrToggled", "else"), ("BrShow", "execute"))
    g.link(("GetShow", "ShowCells"), ("BrShow", "Condition"))
    # off: clear (cheap, every tick while off is fine only when something is there)
    off_in, off_mid = clear_layer("OffClearB", ("GetBlockedLayer", "BlockedLayer"), 1000, 300)
    g.link(("BrShow", "else"), off_in)
    off_in2, off_mid2 = clear_layer("OffClearP", ("GetPenaltyLayer", "PenaltyLayer"), 1750, 300)
    g.link(off_mid, off_in2)
    off_in3, _ = clear_layer("OffClearL", ("GetLandLayer", "LandLayer"), 2500, 300)
    g.link(off_mid2, off_in3)
    g.call("Now", STATICS, "GetRealTimeSeconds", 1000, 1400, [("ReturnValue", "out", DOUBLE, None)])
    due = dmath(g, "Due", "GreaterEqual_DoubleDouble", ("Now", "ReturnValue"), ("GetNext", "NextCellsDraw"), 1250, 1400, out=BOOL)
    branch(g, "BrDue", 1000, 0)
    g.link(("BrShow", "then"), ("BrDue", "execute"))
    g.link(due, ("BrDue", "Condition"))
    set_self(g, "Later", "NextCellsDraw", DOUBLE, 1250, 0)
    g.link(("BrDue", "then"), ("Later", "execute"))
    g.link(dmath(g, "InASecond", "Add_DoubleDouble", ("Now", "ReturnValue"), None, 1250, 1550, b_default="1.0"), ("Later", "NextCellsDraw"))

    # the layers (made once)
    def ensure_layer(p, var, color_var, getter, after, x):
        is_valid(g, p + "Ok", ISMC, x, 300)
        g.link(getter, (p + "Ok", "Object"))
        branch(g, p + "Br", x, 0)
        g.link(after, (p + "Br", "execute"))
        g.link((p + "Ok", "ReturnValue"), (p + "Br", "Condition"))
        ctype, cdefault = CLASSPIN(ACTORCOMP, ISMC)
        g.node(p + "New", K2 + "K2Node_AddComponentByClass", [], x + 250, -200,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
                ("Class", "in", ctype, cdefault), ("bManualAttachment", "in", BOOL, 'DefaultValue="false"'),
                ("RelativeTransform", "in", STRUCT(TRANSFORM), None), ("ReturnValue", "out", OBJ(ISMC), None)])
        g.link((p + "Br", "else"), (p + "New", "execute"))
        layer = (p + "New", "ReturnValue")
        prev = p + "New"
        for name, cls, func, pins in (
                (p + "Movable", "/Script/CoreUObject.Class'/Script/Engine.SceneComponent'", "SetMobility",
                 [("NewMobility", "in", ['PinType.PinCategory="byte"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/Engine.EComponentMobility'\""], 'DefaultValue="Movable"')]),
                (p + "Absolute", "/Script/CoreUObject.Class'/Script/Engine.SceneComponent'", "SetAbsolute",
                 [("bNewAbsoluteLocation", "in", BOOL, 'DefaultValue="true"'), ("bNewAbsoluteRotation", "in", BOOL, 'DefaultValue="true"'),
                  ("bNewAbsoluteScale", "in", BOOL, 'DefaultValue="true"')]),
                (p + "Mesh", "/Script/CoreUObject.Class'/Script/Engine.StaticMeshComponent'", "SetStaticMesh",
                 [("NewMesh", "in", OBJ("/Script/Engine.StaticMesh"), f"DefaultObject=\"/Script/Engine.StaticMesh'{ROUTE_STRIP}'\""),
                  ("ReturnValue", "out", BOOL, None)]),
                (p + "NoCollide", "/Script/CoreUObject.Class'/Script/Engine.PrimitiveComponent'", "SetCollisionEnabled",
                 [("NewType", "in", ['PinType.PinCategory="byte"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/Engine.ECollisionEnabled'\""], 'DefaultValue="NoCollision"')]),
                (p + "NoShadow", "/Script/CoreUObject.Class'/Script/Engine.PrimitiveComponent'", "SetCastShadow",
                 [("NewCastShadow", "in", BOOL, 'DefaultValue="false"')])):
            g.call(name, cls, func, x + 500, -200,
                   [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ISMC), None)] + pins)
            g.link((prev, "then"), (name, "execute"))
            g.link(layer, (name, "self"))
            prev = name
        g.call(p + "MID", MATLIB, "CreateDynamicMaterialInstance", x + 500, 150,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                ("Parent", "in", OBJ("/Script/Engine.MaterialInterface"), f"DefaultObject=\"/Script/Engine.Material'{ROUTE_LINE_MAT}'\""),
                ("OptionalName", "in", NAME, 'DefaultValue="None"'), ("ReturnValue", "out", OBJ(MID), None)])
        g.link((prev, "then"), (p + "MID", "execute"))
        get_self(g, p + "Color", color_var, STRUCT("/Script/CoreUObject.LinearColor"), x + 500, 450)
        g.call(p + "Tint", f"/Script/CoreUObject.Class'{MID}'", "SetVectorParameterValue", x + 750, 150,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MID), None),
                ("ParameterName", "in", NAME, 'DefaultValue="Color"'), ("Value", "in", STRUCT("/Script/CoreUObject.LinearColor"), None)])
        g.link((p + "MID", "then"), (p + "Tint", "execute"))
        g.link((p + "MID", "ReturnValue"), (p + "Tint", "self"))
        g.link((p + "Color", color_var), (p + "Tint", "Value"))
        g.call(p + "SetMat", "/Script/CoreUObject.Class'/Script/Engine.PrimitiveComponent'", "SetMaterial", x + 1000, 150,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ISMC), None),
                ("ElementIndex", "in", INT, 'DefaultValue="0"'), ("Material", "in", OBJ("/Script/Engine.MaterialInterface"), None)])
        g.link((p + "Tint", "then"), (p + "SetMat", "execute"))
        g.link(layer, (p + "SetMat", "self"))
        g.link((p + "MID", "ReturnValue"), (p + "SetMat", "Material"))
        set_self(g, p + "Keep", var, OBJ(ISMC), x + 1250, 150)
        g.link((p + "SetMat", "then"), (p + "Keep", "execute"))
        g.link(layer, (p + "Keep", var))
        g.node(p + "Ready", K2 + "K2Node_ExecutionSequence", [], x + 1500, 0, [("execute", "in", EXEC, None), ("then_0", "out", EXEC, None)])
        g.link((p + "Keep", "then"), (p + "Ready", "execute"))
        g.link((p + "Br", "then"), (p + "Ready", "execute"))
        return (p + "Ready", "then_0")

    ready_b = ensure_layer("LB", "BlockedLayer", "BlockedCellColor", ("GetBlockedLayer", "BlockedLayer"), ("Later", "then"), 1500)
    ready_p = ensure_layer("LP", "PenaltyLayer", "PenaltyCellColor", ("GetPenaltyLayer", "PenaltyLayer"), ready_b, 3250)
    ready_l = ensure_layer("LL", "LandLayer", "LandCellColor", ("GetLandLayer", "LandLayer"), ready_p, 5000)
    in_b, mid_b = clear_layer("ClearB", ("GetBlockedLayer", "BlockedLayer"), 6750, 0)
    g.link(ready_l, in_b)
    in_p, mid_p0 = clear_layer("ClearP", ("GetPenaltyLayer", "PenaltyLayer"), 7500, 0)
    g.link(mid_b, in_p)
    in_l, mid_p = clear_layer("ClearL", ("GetLandLayer", "LandLayer"), 8250, 0)
    g.link(mid_p0, in_l)

    # the centre cell: the camera's focal point
    g.call("Pawn", STATICS, "GetPlayerPawn", 6250, 400,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ("/Script/Engine.Pawn"), None)])
    g.node("AsPlayPawn", K2 + "K2Node_DynamicCast",
           [f"TargetType=\"/Script/CoreUObject.Class'{PLAYPAWN}'\"", "PureState=Pure"], 6500, 400,
           [("Object", "in", OBJ("/Script/Engine.Pawn"), None), ("AsPawn Play", "out", OBJ(PLAYPAWN), None), ("bSuccess", "out", BOOL, None)])
    g.link(("Pawn", "ReturnValue"), ("AsPlayPawn", "Object"))
    get_member(g, "Focal", PLAYPAWN, "m_currentFocalPoint", STRUCT(VECTOR), 6750, 400)
    g.link(("AsPlayPawn", "AsPawn Play"), ("Focal", "self"))
    set_local(g, "SetCentre", F, "Centre", INT, 6500, 0)
    g.link(mid_p, ("SetCentre", "execute"))
    g.link(cell_key_call(g, "FocalKey", ("Focal", "m_currentFocalPoint"), 6750, 550), ("SetCentre", "Centre"))

    # every cell in the square
    neg = ii(g, "NegR", "Multiply_IntInt", ("GetRadius", "CellsRadius"), None, 6750, 700, b_default="-1")
    for_loop(g, "ForDX", 6750, 0)
    for_loop(g, "ForDY", 7000, 0)
    for lp in ("ForDX", "ForDY"):
        g.link(neg, (lp, "FirstIndex"))
        g.link(("GetRadius", "CellsRadius"), (lp, "LastIndex"))
    g.link(("SetCentre", "then"), ("ForDX", "Exec"))
    g.link(("ForDX", "LoopBody"), ("ForDY", "Exec"))
    key = ii(g, "Key", "Add_IntInt", ii(g, "KeyX", "Add_IntInt", ("GetCentre", "Centre"),
                                          ii(g, "DXOff", "Multiply_IntInt", ("ForDX", "Index"), None, 7000, 850, b_default=KEY_MUL), 7250, 850),
             ("ForDY", "Index"), 7500, 850)
    centre = cell_pos_call(g, "CellCentre", key, 7500, 1000)
    cx, cy, _ = break_vec(g, "CellXY", centre, 7750, 1000)
    x0 = dmath(g, "Left", "Subtract_DoubleDouble", cx, None, 8000, 1000, b_default="45.0")
    loc = make_vec(g, "SquareAt", x0, cy, dmath(g, "Lift", "Add_DoubleDouble", ("GetHeight", "RouteLineHeight"), None, 8000, 1150, b_default="1.0"),
                   8250, 1000)
    g.call("Square", MATHLIB, "MakeTransform", 8500, 1000,
           [("Location", "in", STRUCT(VECTOR), None), ("Rotation", "in", STRUCT(ROTATOR), None),
            ("Scale", "in", STRUCT(VECTOR), 'DefaultValue="0.900000,90.000000,1.000000"'), ("ReturnValue", "out", STRUCT(TRANSFORM), None)])
    g.link(loc, ("Square", "Location"))
    blocked = set_contains(g, "IsBlocked", ("GetBlocked", "Blocked"), key, 7750, 1300)
    g.call("IsNear", MAPLIB, "Map_Contains", 7750, 1450,
           [("TargetMap", "in", MAP_INT_INT, None), ("Key", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetPenalty", "Penalty"), ("IsNear", "TargetMap"))
    g.link(key, ("IsNear", "Key"))
    is_land = set_contains(g, "IsLand", ("GetLand", "LandNext"), key, 7750, 1600)
    branch(g, "BrBlocked", 7250, 0)
    g.link(("ForDY", "LoopBody"), ("BrBlocked", "execute"))
    g.link(blocked, ("BrBlocked", "Condition"))
    branch(g, "BrIsLand", 7375, -150)
    g.link(("BrBlocked", "then"), ("BrIsLand", "execute"))
    g.link(is_land, ("BrIsLand", "Condition"))
    branch(g, "BrNear", 7500, 150)
    g.link(("BrBlocked", "else"), ("BrNear", "execute"))
    g.link(("IsNear", "ReturnValue"), ("BrNear", "Condition"))
    for name, getter, after, x, y in (("AddB", ("GetBlockedLayer", "BlockedLayer"), ("BrIsLand", "else"), 7500, -150),
                                      ("AddL", ("GetLandLayer", "LandLayer"), ("BrIsLand", "then"), 7500, -300),
                                      ("AddP", ("GetPenaltyLayer", "PenaltyLayer"), ("BrNear", "then"), 7750, 150)):
        g.call(name, ISM_C, "AddInstance", x, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ISMC), None),
                ("InstanceTransform", "in", STRUCT(TRANSFORM), None), ("bWorldSpace", "in", BOOL, 'DefaultValue="true"'),
                ("ReturnValue", "out", INT, None)])
        g.link(after, (name, "execute"))
        g.link(getter, (name, "self"))
        g.link(("Square", "ReturnValue"), (name, "InstanceTransform"))
    return g.render()


def debug_setup():
    g = Graph()
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 300)
    cmds = ["Arco_GiveUnlock unlock.navaltradeDock", "Arco_GiveUnlock unlock.freightDock", "Arco_GiveResource planks 200", "Arco_GiveResource bricks 100", "Arco_GiveResource cannedfood 50"]
    prev = None
    for i, cmd in enumerate(cmds):
        n = g.call(f"Cmd{i}", SYSLIB, "ExecuteConsoleCommand", 250 * i, 0,
                   [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                    ("Command", "in", STR, f'DefaultValue="{cmd}"')])
        if prev:
            g.link((prev, "then"), (n, "execute"))
        prev = n
    log_msg(g, "LogDebug", "GetModAPI", 250 * len(cmds), 0,
            literal="Debug: sent trade and freight dock unlocks and 200 planks, 100 bricks, 50 cannedfood")
    g.link((prev, "then"), ("LogDebug", "execute"))
    return g.render()


def log_plans():
    """F3: for every ship with an assigned dock, log its plan (action, targets), docks, position and speed."""
    g = Graph()
    PLAN = "/Script/NauticalKit.NauticalPlan"
    OCEAN = "/Script/NauticalKit.NauticalOcean"
    ISLAND = "/Script/NauticalKit.NauticalIsland"
    ACTION = ['PinType.PinCategory="byte"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/NauticalKit.ENauticalAction'\""]
    all_ships(g, "GetAll", 0, 0)
    for_each(g, "ForEach", OBJ(SHIP), 300, 0)
    g.link(("GetAll", "then"), ("ForEach", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForEach", "Array"))
    ship = ("ForEach", "Array Element")

    get_member(g, "Assigned", SHIP, "assignedDock", OBJ(NDOCK), 300, 250)
    g.link(ship, ("Assigned", "self"))
    is_valid(g, "HasDock", NDOCK, 550, 250)
    g.link(("Assigned", "assignedDock"), ("HasDock", "Object"))
    branch(g, "BrHasDock", 600, 0)
    g.link(("ForEach", "LoopBody"), ("BrHasDock", "execute"))
    g.link(("HasDock", "ReturnValue"), ("BrHasDock", "Condition"))

    get_member(g, "GetState", SHIP, "State", STRUCT(SHIPSTATE), 300, 400)
    g.link(ship, ("GetState", "self"))
    break_struct(g, "BreakState", SHIPSTATE,
                 [("shipName", STR), ("dockedDock", OBJ(NDOCK)), ("plan", STRUCT(PLAN)),
                  ("worldLoc", STRUCT(VECTOR)), ("Velocity", T("real", sub="float"))], 550, 400)
    g.link(("GetState", "State"), ("BreakState", "NauticalShipState"))
    break_struct(g, "BreakPlan", PLAN,
                 [("actionGoal", ACTION), ("otherDock", OBJ(NDOCK)), ("otherIsland", OBJ(ISLAND)),
                  ("isOtherLocationValid", BOOL), ("otherLocation", STRUCT(VECTOR)), ("isAutoPlan", BOOL)], 800, 550)
    g.link(("BreakState", "plan"), ("BreakPlan", "NauticalPlan"))

    get_member(g, "Ocean", SHIP, "ocean", OBJ(OCEAN), 800, 250)
    g.link(ship, ("Ocean", "self"))
    g.call("ActionKey", f"/Script/CoreUObject.Class'{OCEAN}'", "GetActionStringKey", 1050, 250,
           [("self", "in", OBJ(OCEAN), None), ("action", "in", ACTION, None), ("ReturnValue", "out", NAME, None)])
    g.link(("Ocean", "ocean"), ("ActionKey", "self"))
    g.link(("BreakPlan", "actionGoal"), ("ActionKey", "action"))

    display_name(g, "AssignedName", NDOCK, 1050, 400)
    g.link(("Assigned", "assignedDock"), ("AssignedName", "Object"))
    display_name(g, "DockedName", NDOCK, 1050, 500)
    g.link(("BreakState", "dockedDock"), ("DockedName", "Object"))
    display_name(g, "OtherDockName", NDOCK, 1050, 600)
    g.link(("BreakPlan", "otherDock"), ("OtherDockName", "Object"))
    display_name(g, "OtherIslandName", ISLAND, 1050, 700)
    g.link(("BreakPlan", "otherIsland"), ("OtherIslandName", "Object"))
    for n, srcpin, y in (("LocStr", ("BreakState", "worldLoc"), 800), ("OtherLocStr", ("BreakPlan", "otherLocation"), 900)):
        g.call(n, STRLIB, "Conv_VectorToString", 1050, y,
               [("InVec", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STR, None)])
        g.link(srcpin, (n, "InVec"))

    s = fmt_to_string(g, "Fmt", "Plan '{name}' assigned: {assigned} docked: {docked} | action: {action} (auto {auto}) "
                      "otherDock: {odock} otherIsland: {oisland} otherLoc({lv}): {oloc} | at {loc} speed {v}",
                      [("name", STR), ("assigned", STR), ("docked", STR), ("action", NAME), ("auto", BOOL),
                       ("odock", STR), ("oisland", STR), ("lv", BOOL), ("oloc", STR), ("loc", STR), ("v", T("real", sub="float"))],
                      1350, 250)
    for arg, srcpin in (("name", ("BreakState", "shipName")), ("assigned", ("AssignedName", "ReturnValue")),
                        ("docked", ("DockedName", "ReturnValue")), ("action", ("ActionKey", "ReturnValue")),
                        ("auto", ("BreakPlan", "isAutoPlan")), ("odock", ("OtherDockName", "ReturnValue")),
                        ("oisland", ("OtherIslandName", "ReturnValue")), ("lv", ("BreakPlan", "isOtherLocationValid")),
                        ("oloc", ("OtherLocStr", "ReturnValue")), ("loc", ("LocStr", "ReturnValue")),
                        ("v", ("BreakState", "Velocity"))):
        g.link(srcpin, ("Fmt", arg))
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 1600, -100)
    log_msg(g, "Log", "GetModAPI", 1850, 0)
    g.link(("BrHasDock", "then"), ("Log", "execute"))
    g.link((s, "ReturnValue"), ("Log", "Msg"))
    return g.render()


def log_nautical_docks():
    """Log every nautical dock: name, state ID / prototype / externalName, assigned ship count, location."""
    g = Graph()
    all_actors(g, "GetAll", NDOCK, 0, 0)
    for_each(g, "ForEach", OBJ(NDOCK), 300, 0)
    g.link(("GetAll", "then"), ("ForEach", "Exec"))
    g.link(("GetAll", "OutActors"), ("ForEach", "Array"))
    nd = ("ForEach", "Array Element")
    get_member(g, "GetState", NDOCK, "State", STRUCT(NDOCKSTATE), 300, 250)
    g.link(nd, ("GetState", "self"))
    break_struct(g, "BreakState", NDOCKSTATE,
                 [("ID", INT), ("prototype", NAME), ("externalName", NAME), ("assignedShips", OBJ(SHIP, "Array"))],
                 550, 250)
    g.link(("GetState", "State"), ("BreakState", "NauticalDockState"))
    g.node("ShipCount", K2 + "K2Node_CallArrayFunction",
           ["FunctionReference=(MemberParent=\"/Script/CoreUObject.Class'/Script/Engine.KismetArrayLibrary'\","
            "MemberName=\"Array_Length\")"],
           800, 400, [("TargetArray", "in", OBJ(SHIP, "Array"), None), ("ReturnValue", "out", INT, None)])
    g.link(("BreakState", "assignedShips"), ("ShipCount", "TargetArray"))
    display_name(g, "Name", NDOCK, 800, 250)
    g.link(nd, ("Name", "Object"))
    loc = actor_loc(g, "Loc", nd, 800, 550)
    g.call("LocStr", STRLIB, "Conv_VectorToString", 1050, 550,
           [("InVec", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STR, None)])
    g.link(loc, ("LocStr", "InVec"))
    s = fmt_to_string(g, "Fmt", "NDock {i} [{name}] ID {id} proto {proto} ext {ext} ships {n} at {loc}",
                      [("i", INT), ("name", STR), ("id", INT), ("proto", NAME), ("ext", NAME), ("n", INT),
                       ("loc", STR)], 1300, 250)
    for arg, srcpin in (("i", ("ForEach", "Array Index")), ("name", ("Name", "ReturnValue")),
                        ("id", ("BreakState", "ID")), ("proto", ("BreakState", "prototype")),
                        ("ext", ("BreakState", "externalName")), ("n", ("ShipCount", "ReturnValue")),
                        ("loc", ("LocStr", "ReturnValue"))):
        g.link(srcpin, ("Fmt", arg))
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 1300, -100)
    log_msg(g, "Log", "GetModAPI", 1600, 0)
    g.link(("ForEach", "LoopBody"), ("Log", "execute"))
    g.link((s, "ReturnValue"), ("Log", "Msg"))
    return g.render()


SPECS = {
    "LogLinks": fn_spec(("ForDocks", "Exec"), locals_=[("Linker", OBJ(LINKER)), ("Src", STR), ("Dst", STR)]),
    "DebugCells": fn_spec(("BrToggled", "execute"), locals_=[("Centre", INT)]),
    "DebugSetup": fn_spec(("Cmd0", "execute")),
    "Stamp": fn_spec(("Pass", "execute"), outputs=[("Result", STR)], returns=[("Pass", "then_0")],
                     values=[("Str", "ReturnValue", "Result")], pure=True),
}


GRAPHS = {
    "Stamp": stamp,
    "CargoToString": cargo_to_string,
    "LogShips": log_ships,
    "IdsToString": ids_to_string,
    "LogLinks": log_links,
    "DebugSetup": debug_setup,
    "LogPlans": log_plans,
    "LogNauticalDocks": log_nautical_docks,
    "DebugCells": debug_cells,
}
