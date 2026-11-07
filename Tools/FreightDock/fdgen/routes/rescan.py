"""Rescan: after buildings change, blocked cells are rebuilt in slices across frames (terrain, coast / penalty,
buildings via their footprints) and every route that now crosses something is replanned. ScanNow does the same in
one go (at load and on F10). ScanPhase: 0 idle, 1 terrain, 2 coast / penalty, 3 buildings, 4 routes.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import (
    BOOL, CLASSPIN, DOUBLE, EXEC, FLOAT, FOOT_MAP, GRIDACTOR_ARRAY, INT, INT_ARRAY, INT_SET,
    INTVECTOR_T, ISM_ARRAY, MAP_INT_INT, MAP_INT_VECTOR, OBJ, STR, STRUCT, T)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, FOOTCELL, FOOTPRINT, GRIDACTOR, ISM, K2, MAPLIB, MATHLIB, MODAPI,
    SETLIB, SMC, STATICS, STRLIB, SYSLIB, TERRAIN, TRANSFORM, VECTOR, VOYAGE_LIB, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    actor_loc, all_actors, arr_item, arrfn, bnot, bop, branch, break_struct, break_vec,
    chain, dmath, for_each, for_loop, get_local, get_member, get_self, ii, inc_self, is_valid, loom_call, map_find,
    set_add, set_clear, set_contains, set_local, set_pin_default, set_self, user_call)
from fdgen.core.text import concat_parts, fmt_to_string, log_msg, to_str
from fdgen.features.docks import dock_id_call
from fdgen.routes.cells import KEY_MUL, add_penalty, cell_key_call, near_end


def log_footprint():
    """Debug LogFootprint(Building): the building's grid footprint as the game holds it (GridActor.liveFootprint) -
    actor location, root cell, facing, whether cells are relative, and every cell as x,y,z=occupancy
    (0 none, 1 full, 2 floor, 3 demand partial, 4 reserved naval space). Local: Text (String)."""
    g = Graph()
    F = "LogFootprint"
    get_local(g, "GetBuilding", F, "Building", OBJ(GRIDACTOR), 0, 400)
    get_local(g, "GetText", F, "Text", STR, 0, 500)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 600)
    building = ("GetBuilding", "Building")
    get_member(g, "Foot", GRIDACTOR, "liveFootprint", STRUCT(FOOTPRINT), 250, 400)
    g.link(building, ("Foot", "self"))
    break_struct(g, "BreakFoot", FOOTPRINT, [("Cells", FOOT_MAP), ("Facing", STRUCT("/Script/ProjectArco.Dir")),
                                            ("rootPosition", INTVECTOR_T), ("IsRelative", BOOL)], 500, 400)
    g.link(("Foot", "liveFootprint"), ("BreakFoot", "GridFootprint"))
    enum_t = lambda e: ['PinType.PinCategory="byte"', f"PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'{e}'\""]
    break_struct(g, "BreakDir", "/Script/ProjectArco.Dir", [("rawDir", enum_t("/Script/ProjectArco.DirectionEnum"))], 750, 550)
    g.link(("BreakFoot", "Facing"), ("BreakDir", "Dir"))
    g.call("DirInt", MATHLIB, "Conv_ByteToInt", 1000, 550, [("InByte", "in", T("byte"), None), ("ReturnValue", "out", INT, None)])
    g.link(("BreakDir", "rawDir"), ("DirInt", "InByte"))
    OBJT = OBJ("/Script/CoreUObject.Object")
    head = concat_parts(g, "Head", [
        "Footprint ", to_str(g, "SName", "GetDisplayName", "Object", OBJT, building, 250, 800, lib=SYSLIB),
        ": actor at ", to_str(g, "SLoc", "Conv_VectorToString", "InVec", STRUCT(VECTOR), actor_loc(g, "Loc", building, 250, 950), 500, 800),
        " root ", to_str(g, "SRoot", "Conv_IntVectorToString", "InIntVec", INTVECTOR_T, ("BreakFoot", "rootPosition"), 750, 800),
        " facing ", to_str(g, "SDir", "Conv_IntToString", "InInt", INT, ("DirInt", "ReturnValue"), 1000, 800),
        " relative ", to_str(g, "SRel", "Conv_BoolToString", "InBool", BOOL, ("BreakFoot", "IsRelative"), 1250, 800),
        " cells:"], 250, 1100)
    set_local(g, "SetHead", F, "Text", STR, 0, 0)
    g.link((head, "ReturnValue"), ("SetHead", "Text"))
    g.call("Keys", MAPLIB, "Map_Keys", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", FOOT_MAP, None),
            ("Keys", "out", INTVECTOR_T + ["PinType.ContainerType=Array"], None)])
    g.link(("SetHead", "then"), ("Keys", "execute"))
    g.link(("BreakFoot", "Cells"), ("Keys", "TargetMap"))
    for_each(g, "ForCells", INTVECTOR_T, 500, 0)
    g.link(("Keys", "then"), ("ForCells", "Exec"))
    g.link(("Keys", "Keys"), ("ForCells", "Array"))
    map_find(g, "Cell", ("BreakFoot", "Cells"), ("ForCells", "Array Element"), FOOT_MAP, STRUCT(FOOTCELL), 750, 300, key_type=INTVECTOR_T)
    break_struct(g, "BreakCell", FOOTCELL, [("occupancy", enum_t("/Script/ProjectArco.EGridOccupancy"))], 1000, 300)
    g.link(("Cell", "Value"), ("BreakCell", "FootprintCell"))
    g.call("OccInt", MATHLIB, "Conv_ByteToInt", 1250, 300, [("InByte", "in", T("byte"), None), ("ReturnValue", "out", INT, None)])
    g.link(("BreakCell", "occupancy"), ("OccInt", "InByte"))
    break_struct(g, "CellXYZ", "/Script/CoreUObject.IntVector", [("X", INT), ("Y", INT), ("Z", INT)], 1000, 450)
    g.link(("ForCells", "Array Element"), ("CellXYZ", "IntVector"))
    item = concat_parts(g, "Item", [("GetText", "Text"), " ",
                                    to_str(g, "SX", "Conv_IntToString", "InInt", INT, ("CellXYZ", "X"), 1250, 600), ",",
                                    to_str(g, "SY", "Conv_IntToString", "InInt", INT, ("CellXYZ", "Y"), 1500, 600), ",",
                                    to_str(g, "SZ", "Conv_IntToString", "InInt", INT, ("CellXYZ", "Z"), 1750, 600), "=",
                                    to_str(g, "SO", "Conv_IntToString", "InInt", INT, ("OccInt", "ReturnValue"), 2000, 600)], 1250, 750)
    set_local(g, "Append", F, "Text", STR, 750, 0)
    g.link(("ForCells", "LoopBody"), ("Append", "execute"))
    g.link((item, "ReturnValue"), ("Append", "Text"))
    log_msg(g, "Log", "GetModAPI", 750, -300)
    g.link(("ForCells", "Completed"), ("Log", "execute"))
    g.link(("GetText", "Text"), ("Log", "Msg"))
    return g.render()


def read_footprint():
    """ReadFootprint(Building) -> Has, LoX, HiX, LoY, HiY: fills FootCells with the map cells (CellKey) holding the
    building's full or floor tiles (GridActor.liveFootprint, absolute cells, height layer 0 and up; a tile is 50
    units, centred at tile * 50 + 25) and returns their cell range. Has is false when no tile counts (no footprint,
    relative cells, or all below the surface). Locals: Found, MinX/MaxX/MinY/MaxY."""
    g = Graph()
    F = "ReadFootprint"
    get_local(g, "GetBuilding", F, "Building", OBJ(GRIDACTOR), 0, 400)
    get_self(g, "GetFoot", "FootCells", INT_SET, 0, 500)
    building = ("GetBuilding", "Building")
    set_clear(g, "ClearFoot", ("GetFoot", "FootCells"), 0, 0)
    for i, (var, lit) in enumerate((("Found", "false"), ("MinX", "999999"), ("MaxX", "-999999"), ("MinY", "999999"), ("MaxY", "-999999"))):
        g.node("Init" + var, K2 + "K2Node_VariableSet", [local_var(F, var)], 250 + 250 * i, 0,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                (var, "in", BOOL if var == "Found" else INT, f'DefaultValue="{lit}"'), ("Output_Get", "out", BOOL if var == "Found" else INT, None)])
    chain(g, "ClearFoot", "InitFound", "InitMinX", "InitMaxX", "InitMinY", "InitMaxY")
    get_member(g, "Foot", GRIDACTOR, "liveFootprint", STRUCT(FOOTPRINT), 250, 400)
    g.link(building, ("Foot", "self"))
    break_struct(g, "BreakFoot", FOOTPRINT, [("Cells", FOOT_MAP), ("IsRelative", BOOL)], 500, 400)
    g.link(("Foot", "liveFootprint"), ("BreakFoot", "GridFootprint"))
    g.call("Keys", MAPLIB, "Map_Keys", 1500, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", FOOT_MAP, None),
            ("Keys", "out", INTVECTOR_T + ["PinType.ContainerType=Array"], None)])
    g.link(("InitMaxY", "then"), ("Keys", "execute"))
    g.link(("BreakFoot", "Cells"), ("Keys", "TargetMap"))
    for_each(g, "ForCells", INTVECTOR_T, 1750, 0)
    g.link(("Keys", "then"), ("ForCells", "Exec"))
    g.link(("Keys", "Keys"), ("ForCells", "Array"))
    map_find(g, "Cell", ("BreakFoot", "Cells"), ("ForCells", "Array Element"), FOOT_MAP, STRUCT(FOOTCELL), 750, 700, key_type=INTVECTOR_T)
    break_struct(g, "BreakCell", FOOTCELL, [("occupancy", ['PinType.PinCategory="byte"',
                 "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/ProjectArco.EGridOccupancy'\""])], 1000, 700)
    g.link(("Cell", "Value"), ("BreakCell", "FootprintCell"))
    g.call("OccInt", MATHLIB, "Conv_ByteToInt", 1250, 700, [("InByte", "in", T("byte"), None), ("ReturnValue", "out", INT, None)])
    g.link(("BreakCell", "occupancy"), ("OccInt", "InByte"))
    occ = ("OccInt", "ReturnValue")
    break_struct(g, "Tile", "/Script/CoreUObject.IntVector", [("X", INT), ("Y", INT), ("Z", INT)], 1000, 900)
    g.link(("ForCells", "Array Element"), ("Tile", "IntVector"))
    solid = bop(g, "Solid", "BooleanOR", ii(g, "IsFull", "EqualEqual_IntInt", occ, None, 1500, 700, b_default="1", out=BOOL),
                ii(g, "IsFloor", "EqualEqual_IntInt", occ, None, 1500, 800, b_default="2", out=BOOL), 1750, 700)
    g.call("Absolute", MATHLIB, "Not_PreBool", 750, 550, [("A", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("BreakFoot", "IsRelative"), ("Absolute", "A"))
    keep = bop(g, "Keep0", "BooleanAND", solid, ii(g, "Surface", "GreaterEqual_IntInt", ("Tile", "Z"), None, 1500, 900, b_default="0", out=BOOL), 2000, 700)
    keep = bop(g, "Keep", "BooleanAND", keep, ("Absolute", "ReturnValue"), 2250, 700)
    branch(g, "BrKeep", 2000, 0)
    g.link(("ForCells", "LoopBody"), ("BrKeep", "execute"))
    g.link(keep, ("BrKeep", "Condition"))
    centre = []
    for axis, y in (("X", 1100), ("Y", 1250)):
        w = ii(g, f"Centre{axis}", "Add_IntInt", ii(g, f"Scale{axis}", "Multiply_IntInt", ("Tile", axis), None, 1250, y, b_default="50"),
               None, 1500, y, b_default="25")
        g.call(f"Dbl{axis}", MATHLIB, "Conv_IntToDouble", 1750, y, [("inInt", "in", INT, None), ("ReturnValue", "out", DOUBLE, None)])
        g.link(w, (f"Dbl{axis}", "inInt"))
        centre.append((f"Dbl{axis}", "ReturnValue"))
    g.call("TilePos", MATHLIB, "MakeVector", 2000, 1150,
           [("X", "in", DOUBLE, None), ("Y", "in", DOUBLE, None), ("Z", "in", DOUBLE, 'DefaultValue="0.0"'), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(centre[0], ("TilePos", "X"))
    g.link(centre[1], ("TilePos", "Y"))
    key = cell_key_call(g, "TileKey", ("TilePos", "ReturnValue"), 2250, 1150)
    set_add(g, "AddFoot", ("GetFoot", "FootCells"), key, 2250, 0)
    g.link(("BrKeep", "then"), ("AddFoot", "execute"))
    g.node("SetFound", K2 + "K2Node_VariableSet", [local_var(F, "Found")], 2500, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Found", "in", BOOL, 'DefaultValue="true"'), ("Output_Get", "out", BOOL, None)])
    g.link(("AddFoot", "then"), ("SetFound", "execute"))
    kx = ii(g, "KeyX", "Divide_IntInt", key, None, 2500, 1400, b_default=KEY_MUL)
    ky = ii(g, "KeyY", "Percent_IntInt", key, None, 2500, 1500, b_default=KEY_MUL)
    prev = "SetFound"
    for i, (var, func, src) in enumerate((("MinX", "Min", kx), ("MaxX", "Max", kx), ("MinY", "Min", ky), ("MaxY", "Max", ky))):
        get_local(g, "Get" + var, F, var, INT, 2750 + 250 * i, 1600)
        set_local(g, "Set" + var, F, var, INT, 2750 + 250 * i, 0)
        g.link(ii(g, "Fold" + var, func, ("Get" + var, var), src, 2750 + 250 * i, 1400), ("Set" + var, var))
        g.link((prev, "then"), ("Set" + var, "execute"))
        prev = "Set" + var
    for var, t in (("Found", BOOL), ("MinX", INT), ("MaxX", INT), ("MinY", INT), ("MaxY", INT)):
        get_local(g, "Ret" + var, F, var, t, 3000, -300)
    return g.render()


def phase_is(g, name, n, x, y):
    get_self(g, name + "Get", "ScanPhase", INT, x - 250, y)
    return ii(g, name, "EqualEqual_IntInt", (name + "Get", "ScanPhase"), None, x, y, b_default=str(n), out=BOOL)


def set_phase(g, name, n, x, y):
    return set_self(g, name, "ScanPhase", INT, x, y, literal=str(n))


def rescan_begin():
    """RescanBegin: clear the next map and list the terrain's instanced meshes; start phase 1."""
    g = Graph()
    get_self(g, "GetBlockedNext", "BlockedNext", INT_SET, 0, 400)
    get_self(g, "GetLandNext", "LandNext", INT_SET, 0, 500)
    get_self(g, "GetPenaltyNext", "PenaltyNext", MAP_INT_INT, 0, 600)
    set_clear(g, "ClearBlocked", ("GetBlockedNext", "BlockedNext"), 0, 0)
    set_clear(g, "ClearLand", ("GetLandNext", "LandNext"), 250, 0)
    g.call("ClearPenalty", MAPLIB, "Map_Clear", 500, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_INT_INT, None)])
    g.link(("GetPenaltyNext", "PenaltyNext"), ("ClearPenalty", "TargetMap"))
    all_actors(g, "GetTerrain", TERRAIN, 750, 0)
    chain(g, "ClearBlocked", "ClearLand", "ClearPenalty", "GetTerrain")
    g.node("Terrain0", K2 + "K2Node_GetArrayItem", [], 1000, 300,
           [("Array", "in", OBJ(TERRAIN, "Array"), None), ("Dimension 1", "in", INT, 'DefaultValue="0"'),
            ("Output", "out", OBJ(TERRAIN), None)])
    g.link(("GetTerrain", "OutActors"), ("Terrain0", "Array"))
    ctype, cdefault = CLASSPIN(ACTORCOMP, ISM)
    g.call("GetISMs", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_GetComponentsByClass", 1000, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(ACTOR), None),
            ("ComponentClass", "in", ctype, cdefault), ("ReturnValue", "out", ISM_ARRAY, None)])
    g.link(("Terrain0", "Output"), ("GetISMs", "self"))
    g.link(("GetTerrain", "then"), ("GetISMs", "execute"))
    set_self(g, "SetISMs", "ScanISMs", ISM_ARRAY, 1250, 0)
    g.link(("GetISMs", "then"), ("SetISMs", "execute"))
    g.link(("GetISMs", "ReturnValue"), ("SetISMs", "ScanISMs"))
    set_self(g, "ZeroComp", "ScanComp", INT, 1500, 0, literal="0")
    set_self(g, "ZeroInst", "ScanInst", INT, 1750, 0, literal="0")
    set_phase(g, "Phase1", 1, 2000, 0)
    chain(g, "SetISMs", "ZeroComp", "ZeroInst", "Phase1")
    return g.render()


def scan_terrain_step():
    """ScanTerrainStep: one unit of phase 1 - test a mesh layer, or read one of its blocks into LandNext if that block
    is above water."""
    g = Graph()
    get_self(g, "GetISMs", "ScanISMs", ISM_ARRAY, 0, 600)
    get_self(g, "GetComp", "ScanComp", INT, 0, 700)
    get_self(g, "GetInst", "ScanInst", INT, 0, 800)
    get_self(g, "GetCompLand", "ScanCompLand", BOOL, 0, 900)
    get_self(g, "GetLandNext", "LandNext", INT_SET, 0, 1000)
    arrfn(g, "NISMs", "Array_Length", 250, 600, [("TargetArray", "in", ISM_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetISMs", "ScanISMs"), ("NISMs", "TargetArray"))
    done = ii(g, "AllDone", "GreaterEqual_IntInt", ("GetComp", "ScanComp"), ("NISMs", "ReturnValue"), 500, 600, out=BOOL)
    branch(g, "BrDone", 0, 0)
    g.link(done, ("BrDone", "Condition"))
    # done: LandArr = LandNext, phase 2
    g.call("ToArr", SETLIB, "Set_ToArray", 250, -300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("A", "in", INT_SET, None), ("Result", "out", INT_ARRAY, None)])
    g.link(("GetLandNext", "LandNext"), ("ToArr", "A"))
    g.link(("BrDone", "then"), ("ToArr", "execute"))
    set_self(g, "SetLandArr", "LandArr", INT_ARRAY, 500, -300)
    g.link(("ToArr", "Result"), ("SetLandArr", "LandArr"))
    set_self(g, "ZeroIdx", "ScanIdx", INT, 750, -300, literal="0")
    set_phase(g, "Phase2", 2, 1000, -300)
    chain(g, "ToArr", "SetLandArr", "ZeroIdx", "Phase2")

    ism = arr_item(g, "Comp", ("GetISMs", "ScanISMs"), ("GetComp", "ScanComp"), OBJ(ISM), 250, 1200)
    g.call("Count", f"/Script/CoreUObject.Class'{ISM}'", "GetInstanceCount", 500, 1200,
           [("self", "in", OBJ(ISM), None), ("ReturnValue", "out", INT, None)])
    g.link(ism, ("Count", "self"))

    # first visit of a layer: is it land (Top/Full mesh, first block at or above sea level, any instances)?
    get_member(g, "Mesh", SMC, "StaticMesh", OBJ("/Script/Engine.StaticMesh"), 500, 1350)
    g.link(ism, ("Mesh", "self"))
    mesh = to_str(g, "MeshName", "GetDisplayName", "Object", OBJ("/Script/CoreUObject.Object"), ("Mesh", "StaticMesh"), 750, 1350, lib=SYSLIB)
    flags = []
    for word in ("Top", "Full"):
        g.call(f"Is{word}", STRLIB, "Contains", 1000, 1350 + (150 if word == "Full" else 0),
               [("SearchIn", "in", STR, None), ("Substring", "in", STR, f'DefaultValue="{word}"'),
                ("bUseCase", "in", BOOL, 'DefaultValue="true"'), ("bSearchFromEnd", "in", BOOL, 'DefaultValue="false"'),
                ("ReturnValue", "out", BOOL, None)])
        g.link(mesh, (f"Is{word}", "SearchIn"))
        flags.append((f"Is{word}", "ReturnValue"))
    block = bop(g, "IsBlock", "BooleanOR", flags[0], flags[1], 1250, 1350)

    def inst_loc(prefix, idx_src, x, y, idx_default=None):
        g.call(prefix, f"/Script/CoreUObject.Class'{ISM}'", "GetInstanceTransform", x, y,
               [("self", "in", OBJ(ISM), None), ("InstanceIndex", "in", INT, None if idx_default is None else f'DefaultValue="{idx_default}"'),
                ("OutInstanceTransform", "out", STRUCT(TRANSFORM), None), ("bWorldSpace", "in", BOOL, 'DefaultValue="true"'),
                ("ReturnValue", "out", BOOL, None)])
        g.link(ism, (prefix, "self"))
        if idx_src:
            g.link(idx_src, (prefix, "InstanceIndex"))
        g.call(prefix + "Loc", MATHLIB, "BreakTransform", x + 250, y,
               [("InTransform", "in", STRUCT(TRANSFORM), None), ("Location", "out", STRUCT(VECTOR), None)])
        g.link((prefix, "OutInstanceTransform"), (prefix + "Loc", "InTransform"))
        return (prefix + "Loc", "Location")

    first = inst_loc("First", None, 500, 1650, idx_default=0)
    g.call("FirstXYZ", MATHLIB, "BreakVector", 1000, 1650,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None), ("Z", "out", DOUBLE, None)])
    g.link(first, ("FirstXYZ", "InVec"))
    g.call("AboveWater", MATHLIB, "Greater_DoubleDouble", 1250, 1650,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="-50.0"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("FirstXYZ", "Z"), ("AboveWater", "A"))
    has = ii(g, "HasAny", "Greater_IntInt", ("Count", "ReturnValue"), None, 750, 1200, b_default="0", out=BOOL)
    land = bop(g, "IsLand1", "BooleanAND", block, ("AboveWater", "ReturnValue"), 1500, 1450)
    land = bop(g, "IsLand", "BooleanAND", land, has, 1750, 1350)

    first_visit = ii(g, "FirstVisit", "EqualEqual_IntInt", ("GetInst", "ScanInst"), None, 500, 400, b_default="0", out=BOOL)
    branch(g, "BrFirst", 250, 0)
    g.link(("BrDone", "else"), ("BrFirst", "execute"))
    g.link(first_visit, ("BrFirst", "Condition"))
    set_self(g, "SetCompLand", "ScanCompLand", BOOL, 500, 150)
    g.link(("BrFirst", "then"), ("SetCompLand", "execute"))
    g.link(land, ("SetCompLand", "ScanCompLand"))
    branch(g, "BrLand", 750, 0)
    g.link(("SetCompLand", "then"), ("BrLand", "execute"))
    g.link(("BrFirst", "else"), ("BrLand", "execute"))
    g.link(("GetCompLand", "ScanCompLand"), ("BrLand", "Condition"))

    # not land: next layer
    inc_self(g, "NextComp", "ScanComp", 1000, 300)
    g.link(("BrLand", "else"), ("NextComp", "execute"))
    set_self(g, "ResetInst", "ScanInst", INT, 1250, 300, literal="0")
    g.link(("NextComp", "then"), ("ResetInst", "execute"))

    # land layer: read block ScanInst into LandNext if it's above water itself (a layer can hold submerged blocks -
    # seabed, undersea tunnels - besides its surface ones), advance (next layer after the last block)
    loc = inst_loc("Inst", ("GetInst", "ScanInst"), 1000, 900)
    g.call("InstXYZ", MATHLIB, "BreakVector", 1500, 1050,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None), ("Z", "out", DOUBLE, None)])
    g.link(loc, ("InstXYZ", "InVec"))
    g.call("InstAbove", MATHLIB, "Greater_DoubleDouble", 1750, 1050,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="-50.0"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("InstXYZ", "Z"), ("InstAbove", "A"))
    branch(g, "BrAbove", 1000, -250)
    g.link(("BrLand", "then"), ("BrAbove", "execute"))
    g.link(("InstAbove", "ReturnValue"), ("BrAbove", "Condition"))
    set_add(g, "AddLand", ("GetLandNext", "LandNext"), cell_key_call(g, "InstKey", loc, 1500, 900), 1000, -100)
    g.link(("BrAbove", "then"), ("AddLand", "execute"))
    inc_self(g, "NextInst", "ScanInst", 1250, -100)
    g.link(("AddLand", "then"), ("NextInst", "execute"))
    g.link(("BrAbove", "else"), ("NextInst", "execute"))
    get_self(g, "GetInst2", "ScanInst", INT, 1500, 100)
    layer_done = ii(g, "LayerDone", "GreaterEqual_IntInt", ("GetInst2", "ScanInst"), ("Count", "ReturnValue"), 1750, 100, out=BOOL)
    branch(g, "BrLayerDone", 1500, -100)
    g.link(("NextInst", "then"), ("BrLayerDone", "execute"))
    g.link(layer_done, ("BrLayerDone", "Condition"))
    inc_self(g, "NextComp2", "ScanComp", 1750, -100)
    g.link(("BrLayerDone", "then"), ("NextComp2", "execute"))
    set_self(g, "ResetInst2", "ScanInst", INT, 2000, -100, literal="0")
    g.link(("NextComp2", "then"), ("ResetInst2", "execute"))
    return g.render()


def scan_coast_step():
    """ScanCoastStep: one unit of phase 2 - block one land cell; if it's coastal, spread Penalty around it."""
    g = Graph()
    get_self(g, "GetLandArr", "LandArr", INT_ARRAY, 0, 600)
    get_self(g, "GetIdx", "ScanIdx", INT, 0, 700)
    get_self(g, "GetCell", "ScanCell", INT, 0, 800)
    get_self(g, "GetBlockedNext", "BlockedNext", INT_SET, 0, 900)
    get_self(g, "GetPenaltyNext", "PenaltyNext", MAP_INT_INT, 0, 1000)
    get_self(g, "GetLandNext", "LandNext", INT_SET, 0, 1100)
    get_self(g, "GetClear", "ClearanceCells", INT, 0, 1200)
    arrfn(g, "NLand", "Array_Length", 250, 600, [("TargetArray", "in", INT_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetLandArr", "LandArr"), ("NLand", "TargetArray"))
    done = ii(g, "AllDone", "GreaterEqual_IntInt", ("GetIdx", "ScanIdx"), ("NLand", "ReturnValue"), 500, 600, out=BOOL)
    branch(g, "BrDone", 0, 0)
    g.link(done, ("BrDone", "Condition"))
    # done: list the buildings, phase 3
    all_actors(g, "GetBuildings", GRIDACTOR, 250, -300)
    g.link(("BrDone", "then"), ("GetBuildings", "execute"))
    set_self(g, "SetBuildings", "ScanBuildings", GRIDACTOR_ARRAY, 500, -300)
    g.link(("GetBuildings", "OutActors"), ("SetBuildings", "ScanBuildings"))
    set_self(g, "ZeroIdx", "ScanIdx", INT, 750, -300, literal="0")
    set_phase(g, "Phase3", 3, 1000, -300)
    chain(g, "GetBuildings", "SetBuildings", "ZeroIdx", "Phase3")

    # this cell
    set_self(g, "SetCell", "ScanCell", INT, 250, 0)
    g.link(("BrDone", "else"), ("SetCell", "execute"))
    g.link(arr_item(g, "CellAt", ("GetLandArr", "LandArr"), ("GetIdx", "ScanIdx"), INT, 250, 1400), ("SetCell", "ScanCell"))
    inc_self(g, "NextIdx", "ScanIdx", 500, 0)
    g.link(("SetCell", "then"), ("NextIdx", "execute"))
    cell = ("GetCell", "ScanCell")
    set_add(g, "AddBlocked", ("GetBlockedNext", "BlockedNext"), cell, 750, 0)
    g.link(("NextIdx", "then"), ("AddBlocked", "execute"))
    inland = None
    for i, off in enumerate((KEY_MUL, -KEY_MUL, 1, -1)):
        nb4 = ii(g, f"N4_{i}", "Add_IntInt", cell, None, 500, 1500 + 100 * i, b_default=off)
        has = set_contains(g, f"N4Land{i}", ("GetLandNext", "LandNext"), nb4, 750, 1500 + 100 * i)
        inland = has if inland is None else bop(g, f"Inland{i}", "BooleanAND", inland, has, 1000, 1500 + 100 * i)
    branch(g, "BrCoast", 1000, 0)
    g.link(("AddBlocked", "then"), ("BrCoast", "execute"))
    g.link(inland, ("BrCoast", "Condition"))
    neg = ii(g, "NegClear", "Multiply_IntInt", ("GetClear", "ClearanceCells"), None, 1000, 400, b_default="-1")
    for_loop(g, "ForDX", 1250, 0)
    for_loop(g, "ForDY", 1500, 0)
    for lp in ("ForDX", "ForDY"):
        g.link(neg, (lp, "FirstIndex"))
        g.link(("GetClear", "ClearanceCells"), (lp, "LastIndex"))
    g.link(("BrCoast", "else"), ("ForDX", "Exec"))
    g.link(("ForDX", "LoopBody"), ("ForDY", "Exec"))
    dx = ii(g, "DXOff", "Multiply_IntInt", ("ForDX", "Index"), None, 1250, 400, b_default=KEY_MUL)
    nb = ii(g, "NbA", "Add_IntInt", cell, dx, 1500, 400)
    nb = ii(g, "Nb", "Add_IntInt", nb, ("ForDY", "Index"), 1750, 400)
    g.call("AbsDX", MATHLIB, "Abs_Int", 1250, 550, [("A", "in", INT, None), ("ReturnValue", "out", INT, None)])
    g.link(("ForDX", "Index"), ("AbsDX", "A"))
    g.call("AbsDY", MATHLIB, "Abs_Int", 1250, 650, [("A", "in", INT, None), ("ReturnValue", "out", INT, None)])
    g.link(("ForDY", "Index"), ("AbsDY", "A"))
    dist = ii(g, "Dist", "Max", ("AbsDX", "ReturnValue"), ("AbsDY", "ReturnValue"), 1500, 600)
    reach = ii(g, "Reach", "Add_IntInt", ("GetClear", "ClearanceCells"), None, 1500, 750, b_default="1")
    pen = ii(g, "Pen", "Subtract_IntInt", reach, dist, 1750, 650)
    add_penalty(g, "P", ("GetPenaltyNext", "PenaltyNext"), nb, pen, ("ForDY", "LoopBody"), 1750, 0)
    return g.render()


def scan_building_step():
    """ScanBuildingStep: one unit of phase 3 - block one building's footprint and penalise around it. When all are
    done, swap the new map in (Blocked, Penalty) and move to phase 4. A building with grid tiles (ReadFootprint)
    blocks the cells holding its full and floor tiles; one without blocks its bounds - colliding parts, or all parts
    if nothing collides (floor tiles) - if they reach the surface."""
    g = Graph()
    get_self(g, "GetBuildings", "ScanBuildings", GRIDACTOR_ARRAY, 0, 600)
    get_self(g, "GetIdx", "ScanIdx", INT, 0, 700)
    get_self(g, "GetBlockedNext", "BlockedNext", INT_SET, 0, 800)
    get_self(g, "GetPenaltyNext", "PenaltyNext", MAP_INT_INT, 0, 900)
    get_self(g, "GetClear", "ClearanceCells", INT, 0, 1000)
    arrfn(g, "NBuildings", "Array_Length", 250, 600, [("TargetArray", "in", GRIDACTOR_ARRAY, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetBuildings", "ScanBuildings"), ("NBuildings", "TargetArray"))
    done = ii(g, "AllDone", "GreaterEqual_IntInt", ("GetIdx", "ScanIdx"), ("NBuildings", "ReturnValue"), 500, 600, out=BOOL)
    branch(g, "BrDone", 0, 0)
    g.link(done, ("BrDone", "Condition"))
    # done: swap in, phase 4
    set_self(g, "SwapBlocked", "Blocked", INT_SET, 250, -300)
    g.link(("GetBlockedNext", "BlockedNext"), ("SwapBlocked", "Blocked"))
    g.link(("BrDone", "then"), ("SwapBlocked", "execute"))
    set_self(g, "SwapPenalty", "Penalty", MAP_INT_INT, 500, -300)
    g.link(("GetPenaltyNext", "PenaltyNext"), ("SwapPenalty", "Penalty"))
    user_call(g, "Refresh", "RefreshDocks", 750, -300)
    set_self(g, "ZeroIdx", "ScanIdx", INT, 1000, -300, literal="0")
    set_self(g, "ZeroReplans", "ScanReplans", INT, 1250, -300, literal="0")
    set_phase(g, "Phase4", 4, 1500, -300)
    chain(g, "SwapBlocked", "SwapPenalty", "Refresh", "ZeroIdx", "ZeroReplans", "Phase4")

    b = arr_item(g, "Building", ("GetBuildings", "ScanBuildings"), ("GetIdx", "ScanIdx"), OBJ(GRIDACTOR), 250, 1200)
    is_valid(g, "Exists", GRIDACTOR, 500, 1200)
    g.link(b, ("Exists", "Object"))
    g.call("Bounds", f"/Script/CoreUObject.Class'{ACTOR}'", "GetActorBounds", 500, 1350,
           [("self", "in", OBJ(ACTOR), None), ("bOnlyCollidingComponents", "in", BOOL, 'DefaultValue="true"'),
            ("Origin", "out", STRUCT(VECTOR), None), ("BoxExtent", "out", STRUCT(VECTOR), None),
            ("bIncludeFromChildActors", "in", BOOL, 'DefaultValue="false"')])
    g.link(b, ("Bounds", "self"))
    # no colliding parts (floor tiles): use all of its components instead
    g.call("BoundsAll", f"/Script/CoreUObject.Class'{ACTOR}'", "GetActorBounds", 500, 1500,
           [("self", "in", OBJ(ACTOR), None), ("bOnlyCollidingComponents", "in", BOOL, 'DefaultValue="false"'),
            ("Origin", "out", STRUCT(VECTOR), None), ("BoxExtent", "out", STRUCT(VECTOR), None),
            ("bIncludeFromChildActors", "in", BOOL, 'DefaultValue="false"')])
    g.link(b, ("BoundsAll", "self"))
    g.call("ColLen", MATHLIB, "VSize", 750, 1350, [("A", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Bounds", "BoxExtent"), ("ColLen", "A"))
    g.call("NoCol", MATHLIB, "LessEqual_DoubleDouble", 1000, 1350,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("ColLen", "ReturnValue"), ("NoCol", "A"))
    use_all = ("NoCol", "ReturnValue")
    for part in ("Origin", "BoxExtent"):
        g.call("Pick" + part, MATHLIB, "SelectVector", 1250, 1350 + (100 if part == "BoxExtent" else 0),
               [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("bPickA", "in", BOOL, None),
                ("ReturnValue", "out", STRUCT(VECTOR), None)])
        g.link(("BoundsAll", part), ("Pick" + part, "A"))
        g.link(("Bounds", part), ("Pick" + part, "B"))
        g.link(use_all, ("Pick" + part, "bPickA"))
    origin, extent = ("PickOrigin", "ReturnValue"), ("PickBoxExtent", "ReturnValue")
    g.call("ExtXYZ", MATHLIB, "BreakVector", 750, 1500,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None), ("Z", "out", DOUBLE, None)])
    g.link(extent, ("ExtXYZ", "InVec"))
    g.call("ExtMax", MATHLIB, "FMax", 1000, 1500,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("ExtXYZ", "X"), ("ExtMax", "A"))
    g.link(("ExtXYZ", "Y"), ("ExtMax", "B"))
    g.call("HasSize", MATHLIB, "Greater_DoubleDouble", 1250, 1500,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("ExtMax", "ReturnValue"), ("HasSize", "A"))
    # unplaced / pooled actors sit exactly at the world origin
    g.call("Loc", f"/Script/CoreUObject.Class'{ACTOR}'", "K2_GetActorLocation", 1000, 1650,
           [("self", "in", OBJ(ACTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(b, ("Loc", "self"))
    g.call("LocLen", MATHLIB, "VSize", 1250, 1650, [("A", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Loc", "ReturnValue"), ("LocLen", "A"))
    g.call("Placed", MATHLIB, "Greater_DoubleDouble", 1500, 1650,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("LocLen", "ReturnValue"), ("Placed", "A"))
    oz = break_vec(g, "OriginXYZ", origin, 1000, 1800)[2]
    top = dmath(g, "Top", "Add_DoubleDouble", oz, ("ExtXYZ", "Z"), 1250, 1800)
    above = dmath(g, "ReachesSurface", "Greater_DoubleDouble", top, None, 1500, 1800, b_default="-50.0", out=BOOL)
    user_call(g, "ReadFoot", "ReadFootprint", 250, -150, ins=[("Building", OBJ(GRIDACTOR))],
              outs=[("Has", BOOL), ("LoX", INT), ("HiX", INT), ("LoY", INT), ("HiY", INT)])
    g.link(b, ("ReadFoot", "Building"))
    has = ("ReadFoot", "Has")
    use = bop(g, "Use00", "BooleanAND", ("HasSize", "ReturnValue"), above, 1500, 1350)
    use = bop(g, "Use0", "BooleanOR", use, has, 1600, 1500)
    use = bop(g, "Use", "BooleanAND", use, ("Placed", "ReturnValue"), 1750, 1350)
    branch(g, "BrExists", 125, 0)
    g.link(("BrDone", "else"), ("BrExists", "execute"))
    g.link(("Exists", "ReturnValue"), ("BrExists", "Condition"))
    g.link(("BrExists", "then"), ("ReadFoot", "execute"))
    branch(g, "BrUse", 250, 0)
    g.link(("ReadFoot", "then"), ("BrUse", "execute"))
    g.link(use, ("BrUse", "Condition"))
    inc_self(g, "NextIdx", "ScanIdx", 500, 300)
    g.link(("BrUse", "else"), ("NextIdx", "execute"))
    g.link(("BrExists", "else"), ("NextIdx", "execute"))

    g.call("Lo", MATHLIB, "Subtract_VectorVector", 750, 1700,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(origin, ("Lo", "A"))
    g.link(extent, ("Lo", "B"))
    g.call("Hi", MATHLIB, "Add_VectorVector", 750, 1850,
           [("A", "in", STRUCT(VECTOR), None), ("B", "in", STRUCT(VECTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(origin, ("Hi", "A"))
    g.link(extent, ("Hi", "B"))
    k0 = cell_key_call(g, "K0", ("Lo", "ReturnValue"), 1000, 1700)
    k1 = cell_key_call(g, "K1", ("Hi", "ReturnValue"), 1000, 1850)
    rng, raw = {}, {}
    for axis, func, y in (("X", "Divide_IntInt", 2000), ("Y", "Percent_IntInt", 2300)):
        a = ii(g, f"Lo{axis}", func, k0, None, 1250, y, b_default=KEY_MUL)
        bb = ii(g, f"Hi{axis}", func, k1, None, 1250, y + 100, b_default=KEY_MUL)
        picked = []
        for end, src, fy in (("Lo", a, y + 200), ("Hi", bb, y + 250)):
            n = f"Pick{end}{axis}"
            g.call(n, MATHLIB, "SelectInt", 1375, fy,
                   [("A", "in", INT, None), ("B", "in", INT, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", INT, None)])
            g.link(("ReadFoot", f"{end}{axis}"), (n, "A"))
            g.link(src, (n, "B"))
            g.link(has, (n, "bPickA"))
            picked.append((n, "ReturnValue"))
        a, bb = picked
        raw[axis] = (a, bb)
        rng[axis] = (ii(g, f"LoG{axis}", "Subtract_IntInt", a, ("GetClear", "ClearanceCells"), 1500, y),
                     ii(g, f"HiG{axis}", "Add_IntInt", bb, ("GetClear", "ClearanceCells"), 1500, y + 100))
    for_loop(g, "ForX", 500, 0)
    for_loop(g, "ForY", 750, 0)
    g.link(("BrUse", "then"), ("ForX", "Exec"))
    g.link(("ForX", "LoopBody"), ("ForY", "Exec"))
    g.link(("ForX", "Completed"), ("NextIdx", "execute"))
    for lp, axis in (("ForX", "X"), ("ForY", "Y")):
        g.link(rng[axis][0], (lp, "FirstIndex"))
        g.link(rng[axis][1], (lp, "LastIndex"))
    hi = ii(g, "KeyHi", "Multiply_IntInt", ("ForX", "Index"), None, 1750, 2000, b_default=KEY_MUL)
    key = ii(g, "Key", "Add_IntInt", hi, ("ForY", "Index"), 2000, 2000)
    outs = []
    for axis, lp, y in (("X", "ForX", 2600), ("Y", "ForY", 2800)):
        below = ii(g, f"Below{axis}", "Subtract_IntInt", raw[axis][0], (lp, "Index"), 1250, y)
        above = ii(g, f"Above{axis}", "Subtract_IntInt", (lp, "Index"), raw[axis][1], 1250, y + 100)
        o = ii(g, f"Out{axis}", "Max", below, above, 1500, y)
        outs.append(ii(g, f"Out0{axis}", "Max", o, None, 1750, y, b_default="0"))
    dist = ii(g, "Dist", "Max", outs[0], outs[1], 2000, 2700)
    in_box = ii(g, "InBox", "EqualEqual_IntInt", dist, None, 2250, 2700, b_default="0", out=BOOL)
    get_self(g, "GetFoot", "FootCells", INT_SET, 2000, 3000)
    in_foot = bop(g, "InFoot", "BooleanAND", has, set_contains(g, "FootHas", ("GetFoot", "FootCells"), key, 2250, 3000), 2500, 3000)
    g.call("NoFoot", MATHLIB, "Not_PreBool", 2250, 2900, [("A", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(has, ("NoFoot", "A"))
    inside = bop(g, "Inside", "BooleanOR", in_foot, bop(g, "InBounds", "BooleanAND", ("NoFoot", "ReturnValue"), in_box, 2500, 2850), 2750, 2900)
    branch(g, "BrInside", 1000, 0)
    g.link(("ForY", "LoopBody"), ("BrInside", "execute"))
    g.link(inside, ("BrInside", "Condition"))
    set_add(g, "AddBlocked", ("GetBlockedNext", "BlockedNext"), key, 1250, -100)
    g.link(("BrInside", "then"), ("AddBlocked", "execute"))
    reach = ii(g, "Reach", "Add_IntInt", ("GetClear", "ClearanceCells"), None, 2250, 2850, b_default="1")
    pen = ii(g, "Pen", "Subtract_IntInt", reach, dist, 2500, 2800)
    add_penalty(g, "P", ("GetPenaltyNext", "PenaltyNext"), key, pen, ("BrInside", "else"), 1250, 100)
    return g.render()


def route_still_clear():
    """RouteStillClear(Id) -> Ok: BPL_FDVoyage.RouteStillClear - dock Id has a stored route and no leg crosses a
    blocked cell or another dock's outline (near-shore cells don't count, so routes through narrow passages aren't
    replanned every rescan)."""
    g = Graph()
    get_local(g, "GetId", "RouteStillClear", "Id", INT, 0, 250)
    loom_call(g, "Call", VOYAGE_LIB, "RouteStillClear", 250, 0, ins=[("Id", INT)], outs=[("ReturnValue", BOOL)])
    g.link(("GetId", "Id"), ("Call", "Id"))
    return g.render()


def scan_route_step():
    """ScanRouteStep: one unit of phase 4 - check one dock's route against the new map, replan it if it now crosses
    something (or has none) or if Blocked has changed size since the last rescan (something was removed or added, so
    a better route may exist). When all are done, note Blocked's size, go idle and schedule the next rescan."""
    g = Graph()
    get_self(g, "GetDocks", "Docks", OBJ(WORKDOCK, "Array"), 0, 600)
    get_self(g, "GetIdx", "ScanIdx", INT, 0, 700)
    arrfn(g, "NDocks", "Array_Length", 250, 600, [("TargetArray", "in", OBJ(WORKDOCK, "Array"), None), ("ReturnValue", "out", INT, None)])
    g.link(("GetDocks", "Docks"), ("NDocks", "TargetArray"))
    done = ii(g, "AllDone", "GreaterEqual_IntInt", ("GetIdx", "ScanIdx"), ("NDocks", "ReturnValue"), 500, 600, out=BOOL)
    branch(g, "BrDone", 0, 0)
    g.link(done, ("BrDone", "Condition"))

    # done: idle; next rescan in RescanSeconds (or 1 s if a building appeared meanwhile)
    set_phase(g, "Idle", 0, 250, -300)
    g.link(("BrDone", "then"), ("Idle", "execute"))
    g.call("Now", STATICS, "GetRealTimeSeconds", 250, -700, [("ReturnValue", "out", DOUBLE, None)])
    get_self(g, "GetEvery", "RescanSeconds", DOUBLE, 250, -600)
    get_self(g, "GetPending", "PendingRescan", BOOL, 250, -500)
    g.call("Wait", MATHLIB, "SelectFloat", 500, -600,
           [("A", "in", DOUBLE, 'DefaultValue="1.0"'), ("B", "in", DOUBLE, None), ("bPickA", "in", BOOL, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetEvery", "RescanSeconds"), ("Wait", "B"))
    g.link(("GetPending", "PendingRescan"), ("Wait", "bPickA"))
    g.call("Due", MATHLIB, "Add_DoubleDouble", 750, -650,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Now", "ReturnValue"), ("Due", "A"))
    g.link(("Wait", "ReturnValue"), ("Due", "B"))
    set_self(g, "SetDue", "NextRescanAt", DOUBLE, 500, -300)
    g.link(("Due", "ReturnValue"), ("SetDue", "NextRescanAt"))
    set_self(g, "ClearPending", "PendingRescan", BOOL, 750, -300, literal="false")
    chain(g, "Idle", "SetDue", "ClearPending")
    get_self(g, "GetBlocked", "Blocked", INT_SET, 750, -900)
    g.call("BlockedLen", SETLIB, "Set_Length", 1000, -900, [("TargetSet", "in", INT_SET, None), ("ReturnValue", "out", INT, None)])
    g.link(("GetBlocked", "Blocked"), ("BlockedLen", "TargetSet"))
    set_self(g, "SetPlanned", "PlannedBlocked", INT, 1000, -450)
    g.link(("ClearPending", "then"), ("SetPlanned", "execute"))
    g.link(("BlockedLen", "ReturnValue"), ("SetPlanned", "PlannedBlocked"))

    # this dock
    dock = arr_item(g, "Dock", ("GetDocks", "Docks"), ("GetIdx", "ScanIdx"), OBJ(WORKDOCK), 250, 900)
    user_call(g, "Target", "TargetOf", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Target", OBJ(WORKDOCK))])
    g.link(("BrDone", "else"), ("Target", "execute"))
    g.link(dock, ("Target", "Dock"))
    is_valid(g, "Paired", WORKDOCK, 500, 300)
    g.link(("Target", "Target"), ("Paired", "Object"))
    branch(g, "BrPaired", 500, 0)
    g.link(("Target", "then"), ("BrPaired", "execute"))
    g.link(("Paired", "ReturnValue"), ("BrPaired", "Condition"))
    user_call(g, "Check", "RouteStillClear", 750, 0, ins=[("Id", INT)], outs=[("Ok", BOOL)])
    g.link(("BrPaired", "then"), ("Check", "execute"))
    g.link(dock_id_call(g, "DockId", dock, 500, 1100), ("Check", "Id"))
    get_self(g, "GetPlanned", "PlannedBlocked", INT, 750, 1250)
    same = ii(g, "SameMap", "EqualEqual_IntInt", ("BlockedLen", "ReturnValue"), ("GetPlanned", "PlannedBlocked"), 1000, 1250, out=BOOL)
    keep = bop(g, "Keep", "BooleanAND", ("Check", "Ok"), same, 1250, 1250)
    branch(g, "BrOk", 1000, 0)
    g.link(("Check", "then"), ("BrOk", "execute"))
    g.link(keep, ("BrOk", "Condition"))
    user_call(g, "Replan", "PlanRoute", 1250, 200, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(("BrOk", "else"), ("Replan", "execute"))
    g.link(dock, ("Replan", "Dock"))
    inc_self(g, "CountReplan", "ScanReplans", 1500, 200)
    g.link(("Replan", "then"), ("CountReplan", "execute"))
    inc_self(g, "NextIdx", "ScanIdx", 1750, 0)
    for src in (("BrPaired", "else"), ("BrOk", "then"), ("CountReplan", "then")):
        g.link(src, ("NextIdx", "execute"))
    return g.render()


def scan_step():
    """ScanStep: one unit of whatever phase the rescan is in."""
    g = Graph()
    prev = None
    for n, func in ((1, "ScanTerrainStep"), (2, "ScanCoastStep"), (3, "ScanBuildingStep"), (4, "ScanRouteStep")):
        x = 250 * (n - 1)
        branch(g, f"BrP{n}", x, 0)
        g.link(phase_is(g, f"Is{n}", n, x + 250, 300 + 100 * n), (f"BrP{n}", "Condition"))
        if prev:
            g.link((prev, "else"), (f"BrP{n}", "execute"))
        user_call(g, func, func, x + 100, 200 + 100 * n)
        g.link((f"BrP{n}", "then"), (func, "execute"))
        prev = f"BrP{n}"
    return g.render()


def rescan_tick():
    """RescanTick (from ScanTick while idle): when NextRescanAt (real time) is reached, start a rescan."""
    g = Graph()
    branch(g, "BrIdle", 0, 0)
    g.link(phase_is(g, "IsIdle", 0, 250, 300), ("BrIdle", "Condition"))
    g.call("Now", STATICS, "GetRealTimeSeconds", 250, 450, [("ReturnValue", "out", DOUBLE, None)])
    get_self(g, "GetDue", "NextRescanAt", DOUBLE, 250, 550)
    g.call("IsDue", MATHLIB, "GreaterEqual_DoubleDouble", 500, 450,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Now", "ReturnValue"), ("IsDue", "A"))
    g.link(("GetDue", "NextRescanAt"), ("IsDue", "B"))
    branch(g, "BrDue", 250, 0)
    g.link(("BrIdle", "then"), ("BrDue", "execute"))
    g.link(("IsDue", "ReturnValue"), ("BrDue", "Condition"))
    user_call(g, "Begin", "RescanBegin", 500, 0)
    g.link(("BrDue", "then"), ("Begin", "execute"))
    return g.render()


def scan_frame():
    """ScanFrame (from ScanTick while a rescan runs): one frame's budget of the current phase (ScanBudget block
    reads; /20 coast cells; /50 buildings; one dock)."""
    g = Graph()
    get_self(g, "GetBudget", "ScanBudget", INT, 0, 400)
    get_self(g, "GetPhase", "ScanPhase", INT, 0, 500)
    sel = None
    for n, div in ((4, "1000000"), (3, "50"), (2, "20")):
        is_n = ii(g, f"Ph{n}", "EqualEqual_IntInt", ("GetPhase", "ScanPhase"), None, 250, 300 + 100 * n, b_default=str(n), out=BOOL)
        g.call(f"Div{n}", MATHLIB, "SelectInt", 500, 300 + 100 * n,
               [("A", "in", INT, f'DefaultValue="{div}"'), ("B", "in", INT, None if sel else 'DefaultValue="1"'),
                ("bPickA", "in", BOOL, None), ("ReturnValue", "out", INT, None)])
        g.link(is_n, (f"Div{n}", "bPickA"))
        if sel:
            g.link(sel, (f"Div{n}", "B"))
        sel = (f"Div{n}", "ReturnValue")
    units = ii(g, "Units", "Divide_IntInt", ("GetBudget", "ScanBudget"), sel, 750, 500)
    units = ii(g, "UnitsMin1", "Max", units, None, 1000, 500, b_default="1")
    for_loop(g, "Work", 0, 0, first=1, with_break=True)
    g.link(units, ("Work", "LastIndex"))
    user_call(g, "Step", "ScanStep", 250, 0)
    g.link(("Work", "LoopBody"), ("Step", "execute"))
    branch(g, "BrFinished", 500, 0)
    g.link(("Step", "then"), ("BrFinished", "execute"))
    g.link(phase_is(g, "IsIdle", 0, 750, 200), ("BrFinished", "Condition"))
    g.link(("BrFinished", "then"), ("Work", "Break"))
    return g.render()


def scan_tick():
    """ScanTick (Event Tick, after DrawArcs - runs while paused, unlike timers): a frame of the running rescan,
    or RescanTick's due check when idle."""
    g = Graph()
    branch(g, "BrIdle", 0, 0)
    g.link(phase_is(g, "IsIdle", 0, 250, 300), ("BrIdle", "Condition"))
    user_call(g, "Due", "RescanTick", 250, -150)
    g.link(("BrIdle", "then"), ("Due", "execute"))
    user_call(g, "Frame", "ScanFrame", 250, 150)
    g.link(("BrIdle", "else"), ("Frame", "execute"))
    return g.render()


def scan_now():
    """ScanNow: run a whole rescan at once (load, F10); ScanTick takes it from there."""
    g = Graph()
    user_call(g, "Begin", "RescanBegin", 0, 0)
    for_loop(g, "Run", 250, 0, first=0, last=10000000, with_break=True)
    g.link(("Begin", "then"), ("Run", "Exec"))
    user_call(g, "Step", "ScanStep", 500, 0)
    g.link(("Run", "LoopBody"), ("Step", "execute"))
    branch(g, "BrFinished", 750, 0)
    g.link(("Step", "then"), ("BrFinished", "execute"))
    g.link(phase_is(g, "IsIdle", 0, 1000, 200), ("BrFinished", "Condition"))
    g.link(("BrFinished", "then"), ("Run", "Break"))
    return g.render()


def on_building_changed():
    """OnBuildingChanged: a building appeared - rescan in about a second (or right after the current rescan)."""
    g = Graph()
    branch(g, "BrIdle", 0, 0)
    g.link(phase_is(g, "IsIdle", 0, 250, 300), ("BrIdle", "Condition"))
    g.call("Now", STATICS, "GetRealTimeSeconds", 250, 450, [("ReturnValue", "out", DOUBLE, None)])
    g.call("Soon", MATHLIB, "Add_DoubleDouble", 500, 450,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, 'DefaultValue="1.0"'), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("Now", "ReturnValue"), ("Soon", "A"))
    set_self(g, "SetDue", "NextRescanAt", DOUBLE, 250, -150)
    g.link(("BrIdle", "then"), ("SetDue", "execute"))
    g.link(("Soon", "ReturnValue"), ("SetDue", "NextRescanAt"))
    set_self(g, "SetPending", "PendingRescan", BOOL, 250, 150, literal="true")
    g.link(("BrIdle", "else"), ("SetPending", "execute"))
    return g.render()


SPECS = {
    "RescanBegin": fn_spec(("ClearBlocked", "execute")),
    "ScanTerrainStep": fn_spec(("BrDone", "execute")),
    "ScanCoastStep": fn_spec(("BrDone", "execute")),
    "ScanBuildingStep": fn_spec(("BrDone", "execute")),
    "RouteStillClear": fn_spec(("Call", "execute"), inputs=[("Id", INT)], outputs=[("Ok", BOOL)],
                               returns=[("Call", "then")], values=[("Call", "ReturnValue", "Ok")]),
    "ScanRouteStep": fn_spec(("BrDone", "execute")),
    "ScanStep": fn_spec(("BrP1", "execute")),
    "ScanFrame": fn_spec(("Work", "execute")),
    "RescanTick": fn_spec(("BrIdle", "execute")),
    "ScanTick": fn_spec(("BrIdle", "execute")),
    "ScanNow": fn_spec(("Begin", "execute")),
    "OnBuildingChanged": fn_spec(("BrIdle", "execute")),
    "LogFootprint": fn_spec(("SetHead", "execute"), inputs=[("Building", OBJ(GRIDACTOR))], locals_=[("Text", STR)]),
    "ReadFootprint": fn_spec(("ClearFoot", "execute"), inputs=[("Building", OBJ(GRIDACTOR))],
                             outputs=[("Has", BOOL), ("LoX", INT), ("HiX", INT), ("LoY", INT), ("HiY", INT)],
                             locals_=[("Found", BOOL, "false"), ("MinX", INT), ("MaxX", INT), ("MinY", INT), ("MaxY", INT)],
                             returns=[("ForCells", "Completed")],
                             values=[("RetFound", "Found", "Has"), ("RetMinX", "MinX", "LoX"), ("RetMaxX", "MaxX", "HiX"),
                                     ("RetMinY", "MinY", "LoY"), ("RetMaxY", "MaxY", "HiY")]),
}


GRAPHS = {
    "LogFootprint": log_footprint,
    "ReadFootprint": read_footprint,
    "RescanBegin": rescan_begin,
    "ScanTerrainStep": scan_terrain_step,
    "ScanCoastStep": scan_coast_step,
    "ScanBuildingStep": scan_building_step,
    "RouteStillClear": route_still_clear,
    "ScanRouteStep": scan_route_step,
    "ScanStep": scan_step,
    "RescanTick": rescan_tick,
    "ScanFrame": scan_frame,
    "ScanTick": scan_tick,
    "ScanNow": scan_now,
    "OnBuildingChanged": on_building_changed,
}
