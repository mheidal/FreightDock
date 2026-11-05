"""Loading: what the partner island needs (DeficitsFor, RequestFor), what is held and requested, moving goods from
a stockpile into the ship (TransferFrom), and FreightTick, which decides when a loaded ship departs.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import (
    BOOL, DOUBLE, EXEC, INT, INT_ARRAY, INT_SET, MAP_INT_ACTOR, MAP_INT_DOUBLE,
    MAP_NAME_INT, MAP_NAME_TO, NAME, NAME_ARRAY, OBJ, SEARCHCASE_PIN, STR, STR_ARRAY, STR_SET, STRUCT)
from fdgen.core.paths import (
    CARGO, GRIDACTOR, ITEM, K2, LINKER, MAPLIB, MAPLOAD_C, MATHLIB, MODAPI, RESBUILDING, RESCOLL,
    SETLIB, SHIP, SHIPCONFIG, SHIPSTATE, SLOT, STOCKPILE, STORAGETAB, STRLIB, SYSLIB, WORKDOCK)
from fdgen.core.nodes import (
    bnot, branch, break_struct, comp_owner, find_component, for_each, get_local, get_member,
    get_self, ii, int_op, is_valid, make_struct, map_add, map_contains, map_find, map_keys, map_remove, set_fields,
    set_local, set_member, set_pin_default, user_call)
from fdgen.core.specs import fn_spec
from fdgen.core.text import concat_parts, fmt_to_string, log_msg, to_str
from fdgen.features.docks import dock_id_call


def deficits_for():
    """Sum of unmet requests over the dock's output warehouses (the game's "Deliver to", StockpileLinker.m_destStockpileIds): the game's
    logistics deficits, or for a "Keep empty" warehouse (which reports none) KeepEmptyDeficits."""
    g = Graph()
    F = "DeficitsFor"
    get_local(g, "GetCountsToClear", F, "Counts", MAP_NAME_INT, 0, -200)
    g.call("ClearCounts", MAPLIB, "Map_Clear", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_NAME_INT, None)])
    g.link(("GetCountsToClear", "Counts"), ("ClearCounts", "TargetMap"))
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    comp_owner(g, "DockOwner", WORKDOCK, 250, 300)
    g.link(("GetDock", "Dock"), ("DockOwner", "self"))
    linker = find_component(g, "FindLinker", ("DockOwner", "ReturnValue"), LINKER, 500, 300)
    set_local(g, "SetLinker", F, "Linker", OBJ(LINKER), 250, 0)
    g.link(("ClearCounts", "then"), ("SetLinker", "execute"))
    g.link(linker, ("SetLinker", "Linker"))

    get_local(g, "GetLinker", F, "Linker", OBJ(LINKER), 500, 450)
    is_valid(g, "LinkerValid", LINKER, 750, 450)
    g.link(("GetLinker", "Linker"), ("LinkerValid", "Object"))
    branch(g, "BrLinker", 500, 0)
    g.link(("SetLinker", "then"), ("BrLinker", "execute"))
    g.link(("LinkerValid", "ReturnValue"), ("BrLinker", "Condition"))

    get_member(g, "DstIds", LINKER, "m_destStockpileIds", INT_SET, 750, 600)
    g.link(("GetLinker", "Linker"), ("DstIds", "self"))
    g.call("ToArray", SETLIB, "Set_ToArray", 750, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("A", "in", INT_SET, None), ("Result", "out", INT_ARRAY, None)])
    g.link(("BrLinker", "then"), ("ToArray", "execute"))
    g.link(("DstIds", "m_destStockpileIds"), ("ToArray", "A"))
    for_each(g, "ForIds", INT, 1000, 0)
    g.link(("ToArray", "then"), ("ForIds", "Exec"))
    g.link(("ToArray", "Result"), ("ForIds", "Array"))

    user_call(g, "FindBuilding", "BuildingById", 1300, 0, ins=[("Id", INT)], outs=[("Building", OBJ(GRIDACTOR))])
    g.link(("ForIds", "LoopBody"), ("FindBuilding", "execute"))
    g.link(("ForIds", "Array Element"), ("FindBuilding", "Id"))
    storage = find_component(g, "FindStorage", ("FindBuilding", "Building"), RESBUILDING, 1300, 300)
    is_valid(g, "StorageValid", RESBUILDING, 1550, 300)
    g.link(storage, ("StorageValid", "Object"))
    branch(g, "BrStorage", 1550, 0)
    g.link(("FindBuilding", "then"), ("BrStorage", "execute"))
    g.link(("StorageValid", "ReturnValue"), ("BrStorage", "Condition"))

    # "Keep empty" warehouses report no deficits to the game's logistics: work out their requests ourselves
    get_member(g, "ForceEmpty", RESBUILDING, "m_forceEmpty", BOOL, 1550, 450)
    g.link(storage, ("ForceEmpty", "self"))
    branch(g, "BrForceEmpty", 1800, 0)
    g.link(("BrStorage", "then"), ("BrForceEmpty", "execute"))
    g.link(("ForceEmpty", "m_forceEmpty"), ("BrForceEmpty", "Condition"))
    user_call(g, "KeepEmpty", "KeepEmptyDeficits", 2050, -250, ins=[("Storage", OBJ(RESBUILDING))],
              outs=[("Deficit", MAP_NAME_INT)])
    g.link(("BrForceEmpty", "then"), ("KeepEmpty", "execute"))
    g.link(storage, ("KeepEmpty", "Storage"))
    set_local(g, "SetKeepEmpty", F, "Deficit", MAP_NAME_INT, 2300, -250)
    g.link(("KeepEmpty", "then"), ("SetKeepEmpty", "execute"))
    g.link(("KeepEmpty", "Deficit"), ("SetKeepEmpty", "Deficit"))

    g.call("GetDeficits", f"/Script/CoreUObject.Class'{RESBUILDING}'", "GetLogisticsDeficitsAsCollection", 1800, 300,
           [("self", "in", OBJ(RESBUILDING), None), ("ReturnValue", "out", STRUCT(RESCOLL), None)])
    g.link(storage, ("GetDeficits", "self"))
    break_struct(g, "BreakDeficits", RESCOLL, [("counts", MAP_NAME_INT)], 2050, 300)
    g.link(("GetDeficits", "ReturnValue"), ("BreakDeficits", "ResourceCollection"))
    set_local(g, "SetDeficit", F, "Deficit", MAP_NAME_INT, 2050, 0)
    g.link(("BrForceEmpty", "else"), ("SetDeficit", "execute"))
    g.link(("BreakDeficits", "counts"), ("SetDeficit", "Deficit"))

    get_local(g, "GetDeficit", F, "Deficit", MAP_NAME_INT, 2300, 450)
    map_keys(g, "DeficitKeys", ("GetDeficit", "Deficit"), MAP_NAME_INT, 2550, 0)
    g.link(("SetDeficit", "then"), ("DeficitKeys", "execute"))
    g.link(("SetKeepEmpty", "then"), ("DeficitKeys", "execute"))
    for_each(g, "ForKeys", NAME, 2800, 0)
    g.link(("DeficitKeys", "then"), ("ForKeys", "Exec"))
    g.link(("DeficitKeys", "Keys"), ("ForKeys", "Array"))
    get_local(g, "GetCounts", F, "Counts", MAP_NAME_INT, 2800, 450)
    map_find(g, "HaveFind", ("GetCounts", "Counts"), ("ForKeys", "Array Element"), MAP_NAME_INT, INT, 3050, 300)
    map_find(g, "NeedFind", ("GetDeficit", "Deficit"), ("ForKeys", "Array Element"), MAP_NAME_INT, INT, 3050, 450)
    total = int_op(g, "Total", "Add_IntInt", ("HaveFind", "Value"), ("NeedFind", "Value"), 3300, 350)
    map_add(g, "AddCount", ("GetCounts", "Counts"), ("ForKeys", "Array Element"), total, MAP_NAME_INT, INT, 3300, 0)
    g.link(("ForKeys", "LoopBody"), ("AddCount", "execute"))

    make_struct(g, "MakeWant", RESCOLL, [("counts", MAP_NAME_INT)], 1000, -250)
    g.link(("GetCounts", "Counts"), ("MakeWant", "counts"))
    return g.render()


def keep_empty_deficits():
    """A "Keep empty" warehouse's requests, which GetLogisticsDeficitsAsCollection leaves out: per slot,
    minHold - count - inbound, where positive."""
    g = Graph()
    F = "KeepEmptyDeficits"
    MAP_SLOTS = MAP_NAME_TO(SLOT)
    get_local(g, "GetStorage", F, "Storage", OBJ(RESBUILDING), 0, 300)
    get_local(g, "GetResult", F, "Result", MAP_NAME_INT, 0, 400)
    get_local(g, "GetInbound", F, "Inbound", MAP_NAME_INT, 0, 500)
    get_local(g, "GetSlots", F, "Slots", MAP_SLOTS, 0, 600)
    get_local(g, "GetNeed", F, "Need", INT, 0, 700)

    g.call("ClearResult", MAPLIB, "Map_Clear", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_NAME_INT, None)])
    g.link(("GetResult", "Result"), ("ClearResult", "TargetMap"))

    g.call("StorageTab", f"/Script/CoreUObject.Class'{RESBUILDING}'", "CalcStorageTab", 250, 250,
           [("self", "in", OBJ(RESBUILDING), None), ("ReturnValue", "out", STRUCT(STORAGETAB), None)])
    g.link(("GetStorage", "Storage"), ("StorageTab", "self"))
    break_struct(g, "BreakTab", STORAGETAB, [("inbound", STRUCT(RESCOLL))], 500, 250)
    g.link(("StorageTab", "ReturnValue"), ("BreakTab", "ResourceBuilding_StorageTab"))
    break_struct(g, "BreakInbound", RESCOLL, [("counts", MAP_NAME_INT)], 750, 250)
    g.link(("BreakTab", "inbound"), ("BreakInbound", "ResourceCollection"))
    set_local(g, "SetInbound", F, "Inbound", MAP_NAME_INT, 250, 0)
    g.link(("ClearResult", "then"), ("SetInbound", "execute"))
    g.link(("BreakInbound", "counts"), ("SetInbound", "Inbound"))

    get_member(g, "PileGet", RESBUILDING, "m_stockpile", STRUCT(STOCKPILE), 500, 400)
    g.link(("GetStorage", "Storage"), ("PileGet", "self"))
    break_struct(g, "PileBreak", STOCKPILE, [("Slots", MAP_SLOTS)], 750, 400)
    g.link(("PileGet", "m_stockpile"), ("PileBreak", "Stockpile"))
    set_local(g, "SetSlots", F, "Slots", MAP_SLOTS, 500, 0)
    g.link(("SetInbound", "then"), ("SetSlots", "execute"))
    g.link(("PileBreak", "Slots"), ("SetSlots", "Slots"))

    map_keys(g, "SlotKeys", ("GetSlots", "Slots"), MAP_SLOTS, 750, 0)
    g.link(("SetSlots", "then"), ("SlotKeys", "execute"))
    for_each(g, "ForKeys", NAME, 1000, 0)
    g.link(("SlotKeys", "then"), ("ForKeys", "Exec"))
    g.link(("SlotKeys", "Keys"), ("ForKeys", "Array"))

    key = ("ForKeys", "Array Element")
    map_find(g, "SlotFind", ("GetSlots", "Slots"), key, MAP_SLOTS, STRUCT(SLOT), 1250, 300)
    break_struct(g, "SlotBreak", SLOT, [("count", INT), ("minHold", INT)], 1500, 300)
    g.link(("SlotFind", "Value"), ("SlotBreak", "ResourceStockpileSlot"))
    map_find(g, "InFind", ("GetInbound", "Inbound"), key, MAP_NAME_INT, INT, 1500, 450)
    held = int_op(g, "MinusCount", "Subtract_IntInt", ("SlotBreak", "minHold"), ("SlotBreak", "count"), 1750, 300)
    need = int_op(g, "MinusInbound", "Subtract_IntInt", held, ("InFind", "Value"), 2000, 350)
    set_local(g, "SetNeed", F, "Need", INT, 1250, 0)
    g.link(("ForKeys", "LoopBody"), ("SetNeed", "execute"))
    g.link(need, ("SetNeed", "Need"))
    positive = int_op(g, "NeedPositive", "Greater_IntInt", ("GetNeed", "Need"), None, 1500, 150, b_default="0")
    branch(g, "BrNeed", 1500, 0)
    g.link(("SetNeed", "then"), ("BrNeed", "execute"))
    g.link(positive, ("BrNeed", "Condition"))
    map_add(g, "AddResult", ("GetResult", "Result"), key, ("GetNeed", "Need"), MAP_NAME_INT, INT, 1750, 0)
    g.link(("BrNeed", "then"), ("AddResult", "execute"))
    get_local(g, "GetResultForReturn", F, "Result", MAP_NAME_INT, 1000, -200)
    return g.render()


def request_for():
    """Put Want into the dock's dock-specific supplies, live requirement and input slots. A resource that was in the
    previous request but not in Want leaves the live requirement, and its input slot's capacity goes to 0."""
    g = Graph()
    F = "RequestFor"
    MAP_SLOTS = MAP_NAME_TO(SLOT)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    get_local(g, "GetWant", F, "Want", STRUCT(RESCOLL), 0, 400)
    get_local(g, "GetLive", F, "Live", MAP_NAME_INT, 0, 500)
    get_local(g, "GetSlots", F, "Slots", MAP_SLOTS, 0, 600)
    get_local(g, "GetSlot", F, "Slot", STRUCT(SLOT), 0, 700)
    get_local(g, "GetOld", F, "Old", MAP_NAME_INT, 0, 800)

    get_member(g, "OldGet", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), -250, 300)
    g.link(("GetDock", "Dock"), ("OldGet", "self"))
    break_struct(g, "OldBreak", RESCOLL, [("counts", MAP_NAME_INT)], -250, 450)
    g.link(("OldGet", "m_requiredEmbarkSupplies_dockSpecific"), ("OldBreak", "ResourceCollection"))
    set_local(g, "SetOld", F, "Old", MAP_NAME_INT, -250, 0)
    g.link(("OldBreak", "counts"), ("SetOld", "Old"))
    set_member(g, "SetSpecific", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), 0, 0)
    g.link(("SetOld", "then"), ("SetSpecific", "execute"))
    g.link(("GetDock", "Dock"), ("SetSpecific", "self"))
    g.link(("GetWant", "Want"), ("SetSpecific", "m_requiredEmbarkSupplies_dockSpecific"))

    get_member(g, "LiveGet", WORKDOCK, "m_requiredEmbarkSupplies_live", STRUCT(RESCOLL), 250, 300)
    g.link(("GetDock", "Dock"), ("LiveGet", "self"))
    break_struct(g, "LiveBreak", RESCOLL, [("counts", MAP_NAME_INT)], 500, 300)
    g.link(("LiveGet", "m_requiredEmbarkSupplies_live"), ("LiveBreak", "ResourceCollection"))
    set_local(g, "SetLive", F, "Live", MAP_NAME_INT, 250, 0)
    g.link(("SetSpecific", "then"), ("SetLive", "execute"))
    g.link(("LiveBreak", "counts"), ("SetLive", "Live"))

    get_member(g, "InputGet", WORKDOCK, "m_inputStockpile", STRUCT(STOCKPILE), 500, 450)
    g.link(("GetDock", "Dock"), ("InputGet", "self"))
    break_struct(g, "InputBreak", STOCKPILE, [("Slots", MAP_SLOTS)], 750, 450)
    g.link(("InputGet", "m_inputStockpile"), ("InputBreak", "Stockpile"))
    set_local(g, "SetSlots", F, "Slots", MAP_SLOTS, 500, 0)
    g.link(("SetLive", "then"), ("SetSlots", "execute"))
    g.link(("InputBreak", "Slots"), ("SetSlots", "Slots"))

    break_struct(g, "WantBreak", RESCOLL, [("counts", MAP_NAME_INT)], 750, 600)
    g.link(("GetWant", "Want"), ("WantBreak", "ResourceCollection"))

    # resources dropped from the request: out of the live requirement, input slot capacity 0
    map_keys(g, "OldKeys", ("GetOld", "Old"), MAP_NAME_INT, 750, -600)
    g.link(("SetSlots", "then"), ("OldKeys", "execute"))
    for_each(g, "ForOld", NAME, 1000, -600)
    g.link(("OldKeys", "then"), ("ForOld", "Exec"))
    g.link(("OldKeys", "Keys"), ("ForOld", "Array"))
    old_key = ("ForOld", "Array Element")
    kept = map_contains(g, "StillWanted", ("WantBreak", "counts"), old_key, MAP_NAME_INT, 1250, -450, key_type=NAME)
    branch(g, "BrDropped", 1250, -600)
    g.link(("ForOld", "LoopBody"), ("BrDropped", "execute"))
    g.link(bnot(g, "Dropped", kept, 1250, -350), ("BrDropped", "Condition"))
    map_remove(g, "RemoveLive", ("GetLive", "Live"), old_key, MAP_NAME_INT, 1500, -600, key_type=NAME)
    g.link(("BrDropped", "then"), ("RemoveLive", "execute"))
    map_find(g, "OldSlotFind", ("GetSlots", "Slots"), old_key, MAP_SLOTS, STRUCT(SLOT), 1750, -450)
    branch(g, "BrOldSlot", 1750, -600)
    g.link(("RemoveLive", "then"), ("BrOldSlot", "execute"))
    g.link(("OldSlotFind", "ReturnValue"), ("BrOldSlot", "Condition"))
    set_local(g, "SetOldSlot", F, "Slot", STRUCT(SLOT), 2000, -600)
    g.link(("BrOldSlot", "then"), ("SetOldSlot", "execute"))
    g.link(("OldSlotFind", "Value"), ("SetOldSlot", "Slot"))
    set_fields(g, "ZeroCapacity", SLOT, "capacity", INT, 2250, -600, defaults={"capacity": "0"})
    g.link(("SetOldSlot", "then"), ("ZeroCapacity", "execute"))
    g.link(("GetSlot", "Slot"), ("ZeroCapacity", "StructRef"))
    map_add(g, "PutOldSlot", ("GetSlots", "Slots"), old_key, ("ZeroCapacity", "StructOut"),
            MAP_SLOTS, STRUCT(SLOT), 2500, -600)
    g.link(("ZeroCapacity", "then"), ("PutOldSlot", "execute"))

    map_keys(g, "WantKeys", ("WantBreak", "counts"), MAP_NAME_INT, 750, 0)
    g.link(("ForOld", "Completed"), ("WantKeys", "execute"))
    for_each(g, "ForKeys", NAME, 1000, 0)
    g.link(("WantKeys", "then"), ("ForKeys", "Exec"))
    g.link(("WantKeys", "Keys"), ("ForKeys", "Array"))

    map_find(g, "Amount", ("WantBreak", "counts"), ("ForKeys", "Array Element"), MAP_NAME_INT, INT, 1250, 300)
    map_add(g, "AddLive", ("GetLive", "Live"), ("ForKeys", "Array Element"), ("Amount", "Value"), MAP_NAME_INT, INT, 1250, 0)
    g.link(("ForKeys", "LoopBody"), ("AddLive", "execute"))
    map_find(g, "SlotFind", ("GetSlots", "Slots"), ("ForKeys", "Array Element"), MAP_SLOTS, STRUCT(SLOT), 1500, 300)
    branch(g, "BrHasSlot", 1500, 0)
    g.link(("AddLive", "then"), ("BrHasSlot", "execute"))
    g.link(("SlotFind", "ReturnValue"), ("BrHasSlot", "Condition"))

    set_local(g, "SetSlot", F, "Slot", STRUCT(SLOT), 1750, -150)
    g.link(("BrHasSlot", "then"), ("SetSlot", "execute"))
    g.link(("SlotFind", "Value"), ("SetSlot", "Slot"))
    set_fields(g, "SlotCapacity", SLOT, "capacity", INT, 2000, -150)
    g.link(("SetSlot", "then"), ("SlotCapacity", "execute"))
    g.link(("GetSlot", "Slot"), ("SlotCapacity", "StructRef"))
    g.link(("Amount", "Value"), ("SlotCapacity", "capacity"))
    map_add(g, "AddExisting", ("GetSlots", "Slots"), ("ForKeys", "Array Element"), ("SlotCapacity", "StructOut"),
            MAP_SLOTS, STRUCT(SLOT), 2250, -150)
    g.link(("SlotCapacity", "then"), ("AddExisting", "execute"))
    make_struct(g, "NewSlot", SLOT, [("capacity", INT)], 1750, 150)
    g.link(("Amount", "Value"), ("NewSlot", "capacity"))
    map_add(g, "AddNew", ("GetSlots", "Slots"), ("ForKeys", "Array Element"), ("NewSlot", "ResourceStockpileSlot"),
            MAP_SLOTS, STRUCT(SLOT), 2000, 150)
    g.link(("BrHasSlot", "else"), ("AddNew", "execute"))

    make_struct(g, "MakeLive", RESCOLL, [("counts", MAP_NAME_INT)], 1250, -350)
    g.link(("GetLive", "Live"), ("MakeLive", "counts"))
    set_member(g, "LiveSet", WORKDOCK, "m_requiredEmbarkSupplies_live", STRUCT(RESCOLL), 1500, -350)
    g.link(("ForKeys", "Completed"), ("LiveSet", "execute"))
    g.link(("GetDock", "Dock"), ("LiveSet", "self"))
    g.link(("MakeLive", "ResourceCollection"), ("LiveSet", "m_requiredEmbarkSupplies_live"))
    make_struct(g, "MakeInput", STOCKPILE, [("Slots", MAP_SLOTS)], 1750, -550)
    g.link(("GetSlots", "Slots"), ("MakeInput", "Slots"))
    set_member(g, "InputSet", WORKDOCK, "m_inputStockpile", STRUCT(STOCKPILE), 2000, -350)
    g.link(("LiveSet", "then"), ("InputSet", "execute"))
    g.link(("GetDock", "Dock"), ("InputSet", "self"))
    g.link(("MakeInput", "Stockpile"), ("InputSet", "m_inputStockpile"))
    return g.render()


def transfer_from():
    """Move this dock's freight (dock-specific resources) from its docked ship's hold to the partner's dock cargo."""
    g = Graph()
    F = "TransferFrom"
    MAP_SLOTS = MAP_NAME_TO(SLOT)
    MAP_ITEMS = MAP_NAME_TO(ITEM)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    get_local(g, "GetPartner", F, "Partner", OBJ(WORKDOCK), 0, 400)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 500)
    get_local(g, "GetShipState", F, "ShipState", STRUCT(SHIPSTATE), 0, 600)
    get_local(g, "GetItems", F, "Items", MAP_ITEMS, 0, 700)
    get_local(g, "GetOutSlots", F, "OutSlots", MAP_SLOTS, 0, 800)
    get_local(g, "GetSlot", F, "Slot", STRUCT(SLOT), 0, 900)
    get_local(g, "GetQ", F, "Q", INT, 0, 1000)
    get_local(g, "GetMoved", F, "Moved", INT, 0, 1100)
    get_local(g, "GetWant", F, "Want", MAP_NAME_INT, 0, 1200)

    g.node("ZeroMoved", K2 + "K2Node_VariableSet", [local_var(F, "Moved")], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Moved", "in", INT, 'DefaultValue="0"'), ("Output_Get", "out", INT, None)])
    user_call(g, "FindShip", "ShipAtDock", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Ship", OBJ(SHIP))])
    g.link(("ZeroMoved", "then"), ("FindShip", "execute"))
    g.link(("GetDock", "Dock"), ("FindShip", "Dock"))
    set_local(g, "SetShip", F, "Ship", OBJ(SHIP), 500, 0)
    g.link(("FindShip", "then"), ("SetShip", "execute"))
    g.link(("FindShip", "Ship"), ("SetShip", "Ship"))
    is_valid(g, "ShipValid", SHIP, 750, 200)
    g.link(("GetShip", "Ship"), ("ShipValid", "Object"))
    branch(g, "BrShip", 750, 0)
    g.link(("SetShip", "then"), ("BrShip", "execute"))
    g.link(("ShipValid", "ReturnValue"), ("BrShip", "Condition"))

    get_member(g, "ShipStateGet", SHIP, "State", STRUCT(SHIPSTATE), 1000, 250)
    g.link(("GetShip", "Ship"), ("ShipStateGet", "self"))
    set_local(g, "SetShipState", F, "ShipState", STRUCT(SHIPSTATE), 1000, 0)
    g.link(("BrShip", "then"), ("SetShipState", "execute"))
    g.link(("ShipStateGet", "State"), ("SetShipState", "ShipState"))
    break_struct(g, "HoldState", SHIPSTATE, [("cargo", STRUCT(CARGO))], 1250, 250)
    g.link(("GetShipState", "ShipState"), ("HoldState", "NauticalShipState"))
    break_struct(g, "HoldCargo", CARGO, [("Items", MAP_ITEMS)], 1500, 250)
    g.link(("HoldState", "cargo"), ("HoldCargo", "NauticalCargo"))
    set_local(g, "SetItems", F, "Items", MAP_ITEMS, 1250, 0)
    g.link(("SetShipState", "then"), ("SetItems", "execute"))
    g.link(("HoldCargo", "Items"), ("SetItems", "Items"))

    get_member(g, "SeaGet", WORKDOCK, "m_stockpile_goodsFromSea", STRUCT(STOCKPILE), 1500, 400)
    g.link(("GetPartner", "Partner"), ("SeaGet", "self"))
    break_struct(g, "SeaBreak", STOCKPILE, [("Slots", MAP_SLOTS)], 1750, 400)
    g.link(("SeaGet", "m_stockpile_goodsFromSea"), ("SeaBreak", "Stockpile"))
    set_local(g, "SetOutSlots", F, "OutSlots", MAP_SLOTS, 1500, 0)
    g.link(("SetItems", "then"), ("SetOutSlots", "execute"))
    g.link(("SeaBreak", "Slots"), ("SetOutSlots", "OutSlots"))

    # every resource in the hold is freight (the ship's own food is kept outside the cargo map)
    map_keys(g, "HoldKeys", ("GetItems", "Items"), MAP_ITEMS, 1750, 0)
    user_call(g, "Deficits", "DeficitsFor", 1750, -250, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Want", STRUCT(RESCOLL))])
    g.link(("SetOutSlots", "then"), ("Deficits", "execute"))
    g.link(("GetPartner", "Partner"), ("Deficits", "Dock"))
    break_struct(g, "BreakWant", RESCOLL, [("counts", MAP_NAME_INT)], 2000, -150)
    g.link(("Deficits", "Want"), ("BreakWant", "ResourceCollection"))
    set_local(g, "SetWant", F, "Want", MAP_NAME_INT, 2000, -250)
    g.link(("Deficits", "then"), ("SetWant", "execute"))
    g.link(("BreakWant", "counts"), ("SetWant", "Want"))
    g.link(("SetWant", "then"), ("HoldKeys", "execute"))
    for_each(g, "ForKeys", NAME, 2000, 0)
    g.link(("HoldKeys", "then"), ("ForKeys", "Exec"))
    g.link(("HoldKeys", "Keys"), ("ForKeys", "Array"))

    # per freight resource: is it in the hold?
    map_find(g, "HoldFind", ("GetItems", "Items"), ("ForKeys", "Array Element"), MAP_ITEMS, STRUCT(ITEM), 2250, 300)
    break_struct(g, "HoldItem", ITEM, [("Quantity", DOUBLE)], 2500, 300)
    g.link(("HoldFind", "Value"), ("HoldItem", "NauticalCargoItem"))
    g.call("Trunc", MATHLIB, "FTrunc", 2750, 300,
           [("A", "in", DOUBLE, None), ("ReturnValue", "out", INT, None)])
    g.link(("HoldItem", "Quantity"), ("Trunc", "A"))
    set_local(g, "SetQ", F, "Q", INT, 2250, 0)
    g.link(("ForKeys", "LoopBody"), ("SetQ", "execute"))
    g.link(("Trunc", "ReturnValue"), ("SetQ", "Q"))
    positive = int_op(g, "QPositive", "Greater_IntInt", ("GetQ", "Q"), None, 2500, 150, b_default="0")
    branch(g, "BrQ", 2500, 0)
    g.link(("SetQ", "then"), ("BrQ", "execute"))
    get_self(g, "GetRequested", "Requested", STR_SET, 2500, 450)
    k = req_key(g, "K", dock_id_call(g, "DockId", ("GetDock", "Dock"), 2500, 550), ("ForKeys", "Array Element"), 2750, 550)
    g.call("Wanted", SETLIB, "Set_Contains", 3500, 450,
           [("TargetSet", "in", STR_SET, None), ("ItemToFind", "in", STR, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetRequested", "Requested"), ("Wanted", "TargetSet"))
    g.link(k, ("Wanted", "ItemToFind"))
    partner_want = map_contains(g, "PartnerWants", ("GetWant", "Want"), ("ForKeys", "Array Element"), MAP_NAME_INT,
                                3500, 600, key_type=NAME)
    g.call("FreightKey", MATHLIB, "BooleanOR", 3750, 500,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Wanted", "ReturnValue"), ("FreightKey", "A"))
    g.link(partner_want, ("FreightKey", "B"))
    wanted = ("FreightKey", "ReturnValue")
    g.call("QAndWanted", MATHLIB, "BooleanAND", 2750, 200,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(positive, ("QAndWanted", "A"))
    g.link(wanted, ("QAndWanted", "B"))
    g.link(("QAndWanted", "ReturnValue"), ("BrQ", "Condition"))

    g.call("HoldRemove", MAPLIB, "Map_Remove", 2750, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", MAP_ITEMS, None), ("Key", "in", NAME, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("BrQ", "then"), ("HoldRemove", "execute"))
    g.link(("GetItems", "Items"), ("HoldRemove", "TargetMap"))
    g.link(("ForKeys", "Array Element"), ("HoldRemove", "Key"))

    map_find(g, "SeaFind", ("GetOutSlots", "OutSlots"), ("ForKeys", "Array Element"), MAP_SLOTS, STRUCT(SLOT), 3000, 300)
    branch(g, "BrSeaSlot", 3000, 0)
    g.link(("HoldRemove", "then"), ("BrSeaSlot", "execute"))
    g.link(("SeaFind", "ReturnValue"), ("BrSeaSlot", "Condition"))
    set_local(g, "SetSlot", F, "Slot", STRUCT(SLOT), 3250, -150)
    g.link(("BrSeaSlot", "then"), ("SetSlot", "execute"))
    g.link(("SeaFind", "Value"), ("SetSlot", "Slot"))
    break_struct(g, "SeaSlotBreak", SLOT, [("count", INT)], 3250, 300)
    g.link(("SeaFind", "Value"), ("SeaSlotBreak", "ResourceStockpileSlot"))
    newcount = int_op(g, "NewCount", "Add_IntInt", ("SeaSlotBreak", "count"), ("GetQ", "Q"), 3500, 300)
    set_fields(g, "SlotCount", SLOT, "count", INT, 3500, -150, more=[("capacity", INT)])
    g.link(("SetSlot", "then"), ("SlotCount", "execute"))
    g.link(("GetSlot", "Slot"), ("SlotCount", "StructRef"))
    g.link(newcount, ("SlotCount", "count"))
    g.link(newcount, ("SlotCount", "capacity"))
    map_add(g, "AddExisting", ("GetOutSlots", "OutSlots"), ("ForKeys", "Array Element"), ("SlotCount", "StructOut"),
            MAP_SLOTS, STRUCT(SLOT), 3750, -150)
    g.link(("SlotCount", "then"), ("AddExisting", "execute"))
    make_struct(g, "NewSlot", SLOT, [("count", INT), ("capacity", INT)], 3250, 150)
    g.link(("GetQ", "Q"), ("NewSlot", "count"))
    g.link(("GetQ", "Q"), ("NewSlot", "capacity"))
    map_add(g, "AddNew", ("GetOutSlots", "OutSlots"), ("ForKeys", "Array Element"), ("NewSlot", "ResourceStockpileSlot"),
            MAP_SLOTS, STRUCT(SLOT), 3500, 150)
    g.link(("BrSeaSlot", "else"), ("AddNew", "execute"))
    moved = int_op(g, "MovedPlusQ", "Add_IntInt", ("GetMoved", "Moved"), ("GetQ", "Q"), 3750, 300)
    set_local(g, "AddMoved", F, "Moved", INT, 4000, 0)
    g.link(("AddExisting", "then"), ("AddMoved", "execute"))
    g.link(("AddNew", "then"), ("AddMoved", "execute"))
    g.link(moved, ("AddMoved", "Moved"))

    # after the loop: write the hold and the partner's dock cargo back
    make_struct(g, "MakeCargo", CARGO, [("Items", MAP_ITEMS)], 2250, -400)
    g.link(("GetItems", "Items"), ("MakeCargo", "Items"))
    set_fields(g, "StateCargo", SHIPSTATE, "cargo", STRUCT(CARGO), 2500, -300)
    g.link(("ForKeys", "Completed"), ("StateCargo", "execute"))
    g.link(("GetShipState", "ShipState"), ("StateCargo", "StructRef"))
    g.link(("MakeCargo", "NauticalCargo"), ("StateCargo", "cargo"))
    set_member(g, "ShipSetState", SHIP, "State", STRUCT(SHIPSTATE), 2750, -300)
    g.link(("StateCargo", "then"), ("ShipSetState", "execute"))
    g.link(("GetShip", "Ship"), ("ShipSetState", "self"))
    g.link(("StateCargo", "StructOut"), ("ShipSetState", "State"))
    make_struct(g, "MakeSea", STOCKPILE, [("Slots", MAP_SLOTS)], 2750, -500)
    g.link(("GetOutSlots", "OutSlots"), ("MakeSea", "Slots"))
    set_member(g, "SeaSet", WORKDOCK, "m_stockpile_goodsFromSea", STRUCT(STOCKPILE), 3000, -300)
    g.link(("ShipSetState", "then"), ("SeaSet", "execute"))
    g.link(("GetPartner", "Partner"), ("SeaSet", "self"))
    g.link(("MakeSea", "Stockpile"), ("SeaSet", "m_stockpile_goodsFromSea"))
    get_local(g, "GetMovedForReturn", F, "Moved", INT, 3000, -550)
    return g.render()


def hold_counts():
    """Ship's hold as resource -> whole quantity, plus the total."""
    g = Graph()
    F = "HoldCounts"
    MAP_ITEMS = MAP_NAME_TO(ITEM)
    get_local(g, "GetOut", F, "Out", MAP_NAME_INT, 0, -200)
    g.call("ClearOut", MAPLIB, "Map_Clear", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_NAME_INT, None)])
    g.link(("GetOut", "Out"), ("ClearOut", "TargetMap"))
    g.node("ZeroSum", K2 + "K2Node_VariableSet", [local_var(F, "Sum")], 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Sum", "in", INT, 'DefaultValue="0"'), ("Output_Get", "out", INT, None)])
    g.link(("ClearOut", "then"), ("ZeroSum", "execute"))
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 250, 300)
    is_valid(g, "ShipValid", SHIP, 500, 300)
    g.link(("GetShip", "Ship"), ("ShipValid", "Object"))
    branch(g, "BrShip", 500, 0)
    g.link(("ZeroSum", "then"), ("BrShip", "execute"))
    g.link(("ShipValid", "ReturnValue"), ("BrShip", "Condition"))

    get_member(g, "State", SHIP, "State", STRUCT(SHIPSTATE), 750, 300)
    g.link(("GetShip", "Ship"), ("State", "self"))
    break_struct(g, "BreakState", SHIPSTATE, [("cargo", STRUCT(CARGO))], 1000, 300)
    g.link(("State", "State"), ("BreakState", "NauticalShipState"))
    break_struct(g, "BreakCargo", CARGO, [("Items", MAP_ITEMS)], 1250, 300)
    g.link(("BreakState", "cargo"), ("BreakCargo", "NauticalCargo"))
    map_keys(g, "ItemKeys", ("BreakCargo", "Items"), MAP_ITEMS, 750, 0)
    g.link(("BrShip", "then"), ("ItemKeys", "execute"))
    for_each(g, "ForItems", NAME, 1000, 0)
    g.link(("ItemKeys", "then"), ("ForItems", "Exec"))
    g.link(("ItemKeys", "Keys"), ("ForItems", "Array"))
    map_find(g, "ItemFind", ("BreakCargo", "Items"), ("ForItems", "Array Element"), MAP_ITEMS, STRUCT(ITEM), 1500, 300)
    break_struct(g, "BreakItem", ITEM, [("Quantity", DOUBLE)], 1750, 300)
    g.link(("ItemFind", "Value"), ("BreakItem", "NauticalCargoItem"))
    g.call("Trunc", MATHLIB, "FTrunc", 2000, 300,
           [("A", "in", DOUBLE, None), ("ReturnValue", "out", INT, None)])
    g.link(("BreakItem", "Quantity"), ("Trunc", "A"))
    map_add(g, "AddOut", ("GetOut", "Out"), ("ForItems", "Array Element"), ("Trunc", "ReturnValue"),
            MAP_NAME_INT, INT, 1300, 0)
    g.link(("ForItems", "LoopBody"), ("AddOut", "execute"))
    get_local(g, "GetSum", F, "Sum", INT, 1550, 450)
    total = int_op(g, "SumPlus", "Add_IntInt", ("GetSum", "Sum"), ("Trunc", "ReturnValue"), 2000, 450)
    set_local(g, "SetSum", F, "Sum", INT, 1550, 0)
    g.link(("AddOut", "then"), ("SetSum", "execute"))
    g.link(total, ("SetSum", "Sum"))
    get_local(g, "GetOutForReturn", F, "Out", MAP_NAME_INT, 1000, -350)
    get_local(g, "GetSumForReturn", F, "Sum", INT, 1000, -250)
    return g.render()


LOAD_LIB = "/Script/Engine.BlueprintGeneratedClass'/Game/Mods/FreightDock/Loom/BPL_FDLoad.BPL_FDLoad_C'"


def update_request():
    """The dock's request, planned by the Loom library (BPL_FDLoad.Plan): what is already being carried to the dock
    plus, per resource, a share of the ship's free space, capped by what the input warehouses hold free
    and leaving out resources no hauler has picked up for a while (see BPL_FDLoad.lm). 0 new while NoMore.
    Outputs: Remaining (unmet need the input warehouses can still supply, ignoring space) and InFlight (units waiting at the dock or being carried to it).
    When the request changes, the log line lists every resource's parts and the free space."""
    g = Graph()
    get_local(g, "GetDock", "UpdateRequest", "Dock", OBJ(WORKDOCK), 0, 300)
    get_local(g, "GetPartner", "UpdateRequest", "Partner", OBJ(WORKDOCK), 0, 400)
    get_local(g, "GetShip", "UpdateRequest", "Ship", OBJ(SHIP), 0, 500)
    get_local(g, "GetNoMore", "UpdateRequest", "NoMore", BOOL, 0, 600)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 700)
    g.node("Self", K2 + "K2Node_Self", [], 0, 200, [("self", "out", ['PinType.PinCategory="object"', 'PinType.PinSubCategory="self"'], None)])
    g.call("Plan", LOAD_LIB, "Plan", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("MapLoad", "in", OBJ(MAPLOAD_C), None), ("Dock", "in", OBJ(WORKDOCK), None),
            ("Partner", "in", OBJ(WORKDOCK), None), ("Ship", "in", OBJ(SHIP), None), ("NoMore", "in", BOOL, None),
            ("Request", "out", MAP_NAME_INT, None), ("Remaining", "out", INT, None), ("InFlight", "out", INT, None),
            ("Space", "out", INT, None), ("Detail", "out", STR, None)])
    g.link(("Self", "self"), ("Plan", "MapLoad"))
    g.link(("GetDock", "Dock"), ("Plan", "Dock"))
    g.link(("GetPartner", "Partner"), ("Plan", "Partner"))
    g.link(("GetShip", "Ship"), ("Plan", "Ship"))
    g.link(("GetNoMore", "NoMore"), ("Plan", "NoMore"))

    # only rewrite the dock's request if it changed
    make_struct(g, "MakeResult", RESCOLL, [("counts", MAP_NAME_INT)], 500, 300)
    g.link(("Plan", "Request"), ("MakeResult", "counts"))
    # CollectionToString is hand-built; its output pin is "result"
    user_call(g, "NewStr", "CollectionToString", 750, 300, ins=[("Collection", STRUCT(RESCOLL))],
              outs=[("result", STR)], impure=False)
    g.link(("MakeResult", "ResourceCollection"), ("NewStr", "Collection"))
    get_member(g, "SpecGet", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), 500, 450)
    g.link(("GetDock", "Dock"), ("SpecGet", "self"))
    user_call(g, "OldStr", "CollectionToString", 750, 450, ins=[("Collection", STRUCT(RESCOLL))],
              outs=[("result", STR)], impure=False)
    g.link(("SpecGet", "m_requiredEmbarkSupplies_dockSpecific"), ("OldStr", "Collection"))
    g.call("Changed", STRLIB, "NotEqual_StrStr", 1000, 350,
           [("A", "in", STR, None), ("B", "in", STR, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("NewStr", "result"), ("Changed", "A"))
    g.link(("OldStr", "result"), ("Changed", "B"))
    branch(g, "BrChanged", 500, 0)
    g.link(("Plan", "then"), ("BrChanged", "execute"))
    g.link(("Changed", "ReturnValue"), ("BrChanged", "Condition"))
    user_call(g, "Request", "RequestFor", 750, 0,
              ins=[("Dock", OBJ(WORKDOCK)), ("Want", STRUCT(RESCOLL))])
    g.link(("BrChanged", "then"), ("Request", "execute"))
    g.link(("GetDock", "Dock"), ("Request", "Dock"))
    g.link(("MakeResult", "ResourceCollection"), ("Request", "Want"))
    dock_id = dock_id_call(g, "DockId", ("GetDock", "Dock"), 1000, 600)
    s = fmt_to_string(g, "FmtReq", "Dock {d} request now: {req}[{detail}free space {space}]",
                      [("d", INT), ("req", STR), ("detail", STR), ("space", INT)], 1250, 500)
    g.link(dock_id, ("FmtReq", "d"))
    g.link(("NewStr", "result"), ("FmtReq", "req"))
    g.link(("Plan", "Detail"), ("FmtReq", "detail"))
    g.link(("Plan", "Space"), ("FmtReq", "space"))
    log_msg(g, "LogReq", "GetModAPI", 1000, 0)
    g.link(("Request", "then"), ("LogReq", "execute"))
    g.link((s, "ReturnValue"), ("LogReq", "Msg"))
    return g.render()


CARRIER_WAIT = 30.0   # seconds a ready ship waits for goods still being carried to its dock


def freight_tick():
    """Rule c: depart when full (hold + in flight) / nothing left to request / max wait; deliver TripSeconds later.
    A ship that is ready while goods are still being carried to its dock waits for them first (DepartingSince; the
    request then only covers what is in flight), at most CARRIER_WAIT seconds. The departure log line says why it left."""
    g = Graph()
    F = "FreightTick"
    DEPARTED = ("GetDeparted", "DepartedAt")
    SINCE = ("GetSince", "LoadingSince")
    get_self(g, "GetDocks", "Docks", OBJ(WORKDOCK, "Array"), 0, 300)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 400)
    get_self(g, "GetDeparted", "DepartedAt", MAP_INT_DOUBLE, 0, 500)
    get_self(g, "GetSince", "LoadingSince", MAP_INT_DOUBLE, 0, 600)
    get_self(g, "GetTrip", "TripSeconds", DOUBLE, 0, 700)
    get_self(g, "GetMaxWait", "MaxWaitSeconds", DOUBLE, 0, 800)
    get_local(g, "GetPartner", F, "Partner", OBJ(WORKDOCK), 0, 900)
    get_local(g, "GetId", F, "Id", INT, 0, 1000)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 1100)
    get_local(g, "GetRemaining", F, "Remaining", INT, 0, 1200)
    get_local(g, "GetLoaded", F, "Loaded", INT, 0, 1300)
    get_local(g, "GetFreight", F, "Freight", INT, 0, 1500)
    get_local(g, "GetNow", F, "Now", DOUBLE, 0, 1400)
    get_local(g, "GetInFlight", F, "InFlight", INT, 0, 1600)
    get_local(g, "GetReason", F, "Reason", STR, 0, 1700)
    get_self(g, "GetDeparting", "DepartingSince", MAP_INT_DOUBLE, 0, 1800)
    DEPARTING = ("GetDeparting", "DepartingSince")
    dock = ("ForDocks", "Array Element")

    user_call(g, "Refresh", "RefreshDocks", 0, 0)
    g.call("GameTime", SYSLIB, "GetGameTimeInSeconds", 250, 200, [("ReturnValue", "out", DOUBLE, None)])
    set_local(g, "SetNow", F, "Now", DOUBLE, 250, 0)
    g.link(("Refresh", "then"), ("SetNow", "execute"))
    g.link(("GameTime", "ReturnValue"), ("SetNow", "Now"))
    for_each(g, "ForDocks", OBJ(WORKDOCK), 500, 0)
    g.link(("SetNow", "then"), ("ForDocks", "Exec"))
    g.link(("GetDocks", "Docks"), ("ForDocks", "Array"))

    user_call(g, "FindPartner", "PartnerOf", 800, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Partner", OBJ(WORKDOCK))])
    g.link(("ForDocks", "LoopBody"), ("FindPartner", "execute"))
    g.link(dock, ("FindPartner", "Dock"))
    set_local(g, "SetPartner", F, "Partner", OBJ(WORKDOCK), 1050, 0)
    g.link(("FindPartner", "then"), ("SetPartner", "execute"))
    g.link(("FindPartner", "Partner"), ("SetPartner", "Partner"))
    is_valid(g, "PartnerValid", WORKDOCK, 1300, 200)
    g.link(("GetPartner", "Partner"), ("PartnerValid", "Object"))
    branch(g, "BrPaired", 1300, 0)
    g.link(("SetPartner", "then"), ("BrPaired", "execute"))
    g.link(("PartnerValid", "ReturnValue"), ("BrPaired", "Condition"))

    dock_id = dock_id_call(g, "DockId", dock, 1550, 200)
    set_local(g, "SetId", F, "Id", INT, 1550, 0)
    g.link(("BrPaired", "then"), ("SetId", "execute"))
    g.link(dock_id, ("SetId", "Id"))
    user_call(g, "FindShip", "ShipAtDock", 1800, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Ship", OBJ(SHIP))])
    g.link(("SetId", "then"), ("FindShip", "execute"))
    g.link(dock, ("FindShip", "Dock"))
    set_local(g, "SetShip", F, "Ship", OBJ(SHIP), 2050, 0)
    g.link(("FindShip", "then"), ("SetShip", "execute"))
    g.link(("FindShip", "Ship"), ("SetShip", "Ship"))
    pending = map_contains(g, "Pending", DEPARTING, ("GetId", "Id"), MAP_INT_DOUBLE, 2050, 550)
    user_call(g, "Update", "UpdateRequest", 2300, 400,
              ins=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP)), ("NoMore", BOOL)],
              outs=[("Remaining", INT), ("InFlight", INT)])
    g.link(dock, ("Update", "Dock"))
    g.link(("GetPartner", "Partner"), ("Update", "Partner"))
    g.link(("GetShip", "Ship"), ("Update", "Ship"))
    g.link(pending, ("Update", "NoMore"))
    set_local(g, "SetRemaining", F, "Remaining", INT, 2550, 400)
    g.link(("Update", "then"), ("SetRemaining", "execute"))
    g.link(("Update", "Remaining"), ("SetRemaining", "Remaining"))
    set_local(g, "SetInFlight", F, "InFlight", INT, 2550, 550)
    g.link(("SetRemaining", "then"), ("SetInFlight", "execute"))
    g.link(("Update", "InFlight"), ("SetInFlight", "InFlight"))
    user_call(g, "Hold", "HoldCounts", 2800, 400, ins=[("Ship", OBJ(SHIP))],
              outs=[("Counts", MAP_NAME_INT), ("Total", INT)])
    user_call(g, "Record", "RecordRequested", 2300, 250, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(dock, ("Record", "Dock"))
    g.link(("SetInFlight", "then"), ("Hold", "execute"))
    g.link(("GetShip", "Ship"), ("Hold", "Ship"))
    set_local(g, "SetLoaded", F, "Loaded", INT, 3050, 400)
    g.link(("Hold", "then"), ("SetLoaded", "execute"))
    g.link(("Hold", "Total"), ("SetLoaded", "Loaded"))

    # already under way?
    map_find(g, "DepartedFind", DEPARTED, ("GetId", "Id"), MAP_INT_DOUBLE, DOUBLE, 2300, 200, key_type=INT)
    branch(g, "BrUnderWay", 2300, 0)
    g.link(("SetShip", "then"), ("BrUnderWay", "execute"))
    g.link(("BrUnderWay", "else"), ("Record", "execute"))
    g.link(("Record", "then"), ("Update", "execute"))
    g.link(("DepartedFind", "ReturnValue"), ("BrUnderWay", "Condition"))

    # arrival
    g.call("TripElapsed", MATHLIB, "Subtract_DoubleDouble", 3550, -350,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetNow", "Now"), ("TripElapsed", "A"))
    g.link(("DepartedFind", "Value"), ("TripElapsed", "B"))
    g.call("Arrived", MATHLIB, "GreaterEqual_DoubleDouble", 3800, -350,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("TripElapsed", "ReturnValue"), ("Arrived", "A"))
    g.link(("GetTrip", "TripSeconds"), ("Arrived", "B"))
    branch(g, "BrArrived", 3550, -200)
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 3300, -450)
    on_voyage = map_contains(g, "OnVoyage", ("GetVoyages", "Voyages"), ("GetId", "Id"), MAP_INT_ACTOR, 3300, -350)
    branch(g, "BrVoyage", 3300, -200)
    g.link(("BrUnderWay", "then"), ("BrVoyage", "execute"))
    g.link(on_voyage, ("BrVoyage", "Condition"))
    g.link(("BrVoyage", "else"), ("BrArrived", "execute"))
    g.link(("Arrived", "ReturnValue"), ("BrArrived", "Condition"))
    user_call(g, "Deliver", "TransferFrom", 3800, -200,
              ins=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK))], outs=[("Total", INT)])
    g.link(("BrArrived", "then"), ("Deliver", "execute"))
    g.link(dock, ("Deliver", "Dock"))
    g.link(("GetPartner", "Partner"), ("Deliver", "Partner"))
    for i, (src_map, label) in enumerate(((DEPARTED, "ForgetDeparted"), (SINCE, "ForgetSince"))):
        g.call(label, MAPLIB, "Map_Remove", 4050 + 250 * i, -200,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                ("TargetMap", "in", MAP_INT_DOUBLE, None), ("Key", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
        g.link(src_map, (label, "TargetMap"))
        g.link(("GetId", "Id"), (label, "Key"))
    g.link(("Deliver", "then"), ("ForgetDeparted", "execute"))
    g.link(("ForgetDeparted", "then"), ("ForgetSince", "execute"))
    partner_id = dock_id_call(g, "PartnerId", ("GetPartner", "Partner"), 4050, -450)
    s_arr = fmt_to_string(g, "FmtArrived", "Dock {d} freight arrived at partner {p}: delivered {n}",
                          [("d", INT), ("p", INT), ("n", INT)], 4300, -500)
    g.link(("GetId", "Id"), ("FmtArrived", "d"))
    g.link(partner_id, ("FmtArrived", "p"))
    g.link(("Deliver", "Total"), ("FmtArrived", "n"))
    log_msg(g, "LogArrived", "GetModAPI", 4550, -200)
    user_call(g, "ClearReq", "ClearRequested", 4550, -350, ins=[("Id", INT)])
    g.link(("ForgetSince", "then"), ("ClearReq", "execute"))
    g.link(("GetId", "Id"), ("ClearReq", "Id"))
    g.link(("ClearReq", "then"), ("LogArrived", "execute"))
    g.link((s_arr, "ReturnValue"), ("LogArrived", "Msg"))

    # loading: start the wait clock, then check rule c
    loaded_any = int_op(g, "LoadedAny", "Greater_IntInt", ("GetFreight", "Freight"), None, 3550, 400, b_default="0")
    branch(g, "BrLoaded", 3550, 200)
    user_call(g, "FreightC", "FreightCounts", 3300, 400,
              ins=[("Ship", OBJ(SHIP)), ("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK))], outs=[("Freight", INT)])
    g.link(("SetLoaded", "then"), ("FreightC", "execute"))
    g.link(("GetShip", "Ship"), ("FreightC", "Ship"))
    g.link(dock, ("FreightC", "Dock"))
    g.link(("GetPartner", "Partner"), ("FreightC", "Partner"))
    set_local(g, "SetFreight", F, "Freight", INT, 3300, 200)
    g.link(("FreightC", "then"), ("SetFreight", "execute"))
    g.link(("FreightC", "Freight"), ("SetFreight", "Freight"))
    g.link(("SetFreight", "then"), ("BrLoaded", "execute"))
    g.link(loaded_any, ("BrLoaded", "Condition"))
    map_find(g, "SinceFind", SINCE, ("GetId", "Id"), MAP_INT_DOUBLE, DOUBLE, 3800, 450, key_type=INT)
    branch(g, "BrClockRunning", 3800, 200)
    g.link(("BrLoaded", "then"), ("BrClockRunning", "execute"))
    g.link(("SinceFind", "ReturnValue"), ("BrClockRunning", "Condition"))
    map_add(g, "StartClock", SINCE, ("GetId", "Id"), ("GetNow", "Now"), MAP_INT_DOUBLE, DOUBLE, 4050, 350, key_type=INT)
    g.link(("BrClockRunning", "else"), ("StartClock", "execute"))

    get_member(g, "ShipConfig", SHIP, "config", STRUCT(SHIPCONFIG), 4050, 600)
    g.link(("GetShip", "Ship"), ("ShipConfig", "self"))
    break_struct(g, "BreakConfig", SHIPCONFIG, [("cargoLimit", INT)], 4300, 600)
    g.link(("ShipConfig", "config"), ("BreakConfig", "NauticalShipConfig"))
    aboard_soon = int_op(g, "LoadedPlusFlight", "Add_IntInt", ("GetLoaded", "Loaded"), ("GetInFlight", "InFlight"), 4300, 750)
    full = int_op(g, "Full", "GreaterEqual_IntInt", aboard_soon, ("BreakConfig", "cargoLimit"), 4550, 600)
    all_aboard = int_op(g, "AllAboard", "EqualEqual_IntInt", ("GetRemaining", "Remaining"), None, 4550, 750, b_default="0")
    g.call("Waited", MATHLIB, "Subtract_DoubleDouble", 4300, 900,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetNow", "Now"), ("Waited", "A"))
    g.link(("SinceFind", "Value"), ("Waited", "B"))
    g.call("WaitedEnough", MATHLIB, "GreaterEqual_DoubleDouble", 4550, 900,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Waited", "ReturnValue"), ("WaitedEnough", "A"))
    g.link(("GetMaxWait", "MaxWaitSeconds"), ("WaitedEnough", "B"))
    g.call("FullOrAll", MATHLIB, "BooleanOR", 4800, 650,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(full, ("FullOrAll", "A"))
    g.link(all_aboard, ("FullOrAll", "B"))
    g.call("ShouldGo", MATHLIB, "BooleanOR", 5050, 750,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("FullOrAll", "ReturnValue"), ("ShouldGo", "A"))
    g.link(("WaitedEnough", "ReturnValue"), ("ShouldGo", "B"))
    nothing_carried = int_op(g, "NoneCarried", "EqualEqual_IntInt", ("GetInFlight", "InFlight"), None, 4300, 1100,
                             b_default="0")

    # departure already pending: go once the carriers have arrived, or after CARRIER_WAIT
    branch(g, "BrPending", 4300, 200)
    g.link(("BrClockRunning", "then"), ("BrPending", "execute"))
    g.link(("StartClock", "then"), ("BrPending", "execute"))
    g.link(pending, ("BrPending", "Condition"))
    map_find(g, "PendingFind", DEPARTING, ("GetId", "Id"), MAP_INT_DOUBLE, DOUBLE, 4300, -100, key_type=INT)
    g.call("PendingFor", MATHLIB, "Subtract_DoubleDouble", 4550, -100,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, None), ("ReturnValue", "out", DOUBLE, None)])
    g.link(("GetNow", "Now"), ("PendingFor", "A"))
    g.link(("PendingFind", "Value"), ("PendingFor", "B"))
    g.call("WaitOver", MATHLIB, "GreaterEqual_DoubleDouble", 4800, -100,
           [("A", "in", DOUBLE, None), ("B", "in", DOUBLE, f'DefaultValue="{CARRIER_WAIT}"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("PendingFor", "ReturnValue"), ("WaitOver", "A"))
    g.call("Ready", MATHLIB, "BooleanOR", 5050, -100,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(nothing_carried, ("Ready", "A"))
    g.link(("WaitOver", "ReturnValue"), ("Ready", "B"))
    branch(g, "BrReady", 4550, 50)
    g.link(("BrPending", "then"), ("BrReady", "execute"))
    g.link(("Ready", "ReturnValue"), ("BrReady", "Condition"))
    g.call("WhyPending", MATHLIB, "SelectString", 4800, 100,
           [("A", "in", STR, 'DefaultValue="carriers arrived"'), ("B", "in", STR, 'DefaultValue="carrier wait timed out"'),
            ("bPickA", "in", BOOL, None), ("ReturnValue", "out", STR, None)])
    g.link(nothing_carried, ("WhyPending", "bPickA"))
    set_local(g, "SetReasonPending", F, "Reason", STR, 4800, 50)
    g.link(("BrReady", "then"), ("SetReasonPending", "execute"))
    g.link(("WhyPending", "ReturnValue"), ("SetReasonPending", "Reason"))

    branch(g, "BrDepart", 4550, 200)
    g.link(("BrPending", "else"), ("BrDepart", "execute"))
    g.link(("ShouldGo", "ReturnValue"), ("BrDepart", "Condition"))
    # ready, but goods still on their way to the dock: wait for them
    branch(g, "BrCarrying", 4800, 200)
    g.link(("BrDepart", "then"), ("BrCarrying", "execute"))
    g.link(bnot(g, "SomeCarried", nothing_carried, 4800, 1100), ("BrCarrying", "Condition"))
    map_add(g, "StartPending", DEPARTING, ("GetId", "Id"), ("GetNow", "Now"), MAP_INT_DOUBLE, DOUBLE, 5050, 350, key_type=INT)
    g.link(("BrCarrying", "then"), ("StartPending", "execute"))
    s_wait = fmt_to_string(g, "FmtWaiting",
                           "Dock {d} ready to depart (rule: {rule}), waiting up to {w} s for {n} being carried to the dock",
                           [("d", INT), ("rule", STR), ("w", INT), ("n", INT)], 5300, 500)
    g.link(("GetId", "Id"), ("FmtWaiting", "d"))
    g.link(("GetInFlight", "InFlight"), ("FmtWaiting", "n"))
    set_pin_default(g, "FmtWaiting_wTxt", "Value", str(int(CARRIER_WAIT)))
    log_msg(g, "LogWaiting", "GetModAPI", 5300, 350)
    g.link(("StartPending", "then"), ("LogWaiting", "execute"))
    g.link((s_wait, "ReturnValue"), ("LogWaiting", "Msg"))
    set_local(g, "SetReasonRule", F, "Reason", STR, 5050, 200)
    g.link(("BrCarrying", "else"), ("SetReasonRule", "execute"))

    map_add(g, "Depart", DEPARTED, ("GetId", "Id"), ("GetNow", "Now"), MAP_INT_DOUBLE, DOUBLE, 5300, 200, key_type=INT)
    g.link(("SetReasonRule", "then"), ("Depart", "execute"))
    g.link(("SetReasonPending", "then"), ("Depart", "execute"))
    map_remove(g, "ForgetPending", DEPARTING, ("GetId", "Id"), MAP_INT_DOUBLE, 5550, 200)
    g.link(("Depart", "then"), ("ForgetPending", "execute"))
    partner_id2 = dock_id_call(g, "PartnerId2", ("GetPartner", "Partner"), 5550, 0)
    s_dep = fmt_to_string(g, "FmtDepart", "Dock {d} departs for partner {p} with {n} aboard (still wanted: {r}; {reason})",
                          [("d", INT), ("p", INT), ("n", INT), ("r", INT), ("reason", STR)], 5800, 0)
    g.call("RuleAll", MATHLIB, "SelectString", 5050, 950,
           [("A", "in", STR, 'DefaultValue="all wanted aboard"'), ("B", "in", STR, 'DefaultValue="timer"'),
            ("bPickA", "in", BOOL, None), ("ReturnValue", "out", STR, None)])
    g.link(all_aboard, ("RuleAll", "bPickA"))
    g.call("Rule", MATHLIB, "SelectString", 5300, 950,
           [("A", "in", STR, 'DefaultValue="full"'), ("B", "in", STR, None),
            ("bPickA", "in", BOOL, None), ("ReturnValue", "out", STR, None)])
    g.link(full, ("Rule", "bPickA"))
    g.link(("RuleAll", "ReturnValue"), ("Rule", "B"))
    g.link(("Rule", "ReturnValue"), ("FmtWaiting", "rule"))
    to_rule = concat_parts(g, "RuleText", ["rule: ", ("Rule", "ReturnValue")], 5300, 1250)
    g.link((to_rule, "ReturnValue"), ("SetReasonRule", "Reason"))
    g.link(("GetReason", "Reason"), ("FmtDepart", "reason"))
    g.link(("GetId", "Id"), ("FmtDepart", "d"))
    g.link(partner_id2, ("FmtDepart", "p"))
    g.link(("GetFreight", "Freight"), ("FmtDepart", "n"))
    g.link(("GetRemaining", "Remaining"), ("FmtDepart", "r"))
    log_msg(g, "LogDepart", "GetModAPI", 5800, 200)
    g.link(("ForgetPending", "then"), ("LogDepart", "execute"))
    g.link((s_dep, "ReturnValue"), ("LogDepart", "Msg"))
    user_call(g, "Pause", "PauseLoading", 6050, 200, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(("LogDepart", "then"), ("Pause", "execute"))
    g.link(dock, ("Pause", "Dock"))
    user_call(g, "Voyage", "StartVoyage", 6300, 200,
              ins=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP))])
    g.link(("Pause", "then"), ("Voyage", "execute"))
    g.link(dock, ("Voyage", "Dock"))
    g.link(("GetPartner", "Partner"), ("Voyage", "Partner"))
    g.link(("GetShip", "Ship"), ("Voyage", "Ship"))
    return g.render()


def pause_loading():
    """Stop workers loading: empty dock-specific and live requests, zero the input slots' capacity."""
    g = Graph()
    F = "PauseLoading"
    MAP_SLOTS = MAP_NAME_TO(SLOT)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    get_local(g, "GetEmpty", F, "Empty", MAP_NAME_INT, 0, 400)
    get_local(g, "GetSlots", F, "Slots", MAP_SLOTS, 0, 500)
    get_local(g, "GetSlot", F, "Slot", STRUCT(SLOT), 0, 600)

    g.call("ClearEmpty", MAPLIB, "Map_Clear", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_NAME_INT, None)])
    g.link(("GetEmpty", "Empty"), ("ClearEmpty", "TargetMap"))
    make_struct(g, "MakeEmpty", RESCOLL, [("counts", MAP_NAME_INT)], 250, 250)
    g.link(("GetEmpty", "Empty"), ("MakeEmpty", "counts"))
    set_member(g, "SetSpecific", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), 250, 0)
    g.link(("ClearEmpty", "then"), ("SetSpecific", "execute"))
    g.link(("GetDock", "Dock"), ("SetSpecific", "self"))
    g.link(("MakeEmpty", "ResourceCollection"), ("SetSpecific", "m_requiredEmbarkSupplies_dockSpecific"))
    set_member(g, "SetLive", WORKDOCK, "m_requiredEmbarkSupplies_live", STRUCT(RESCOLL), 500, 0)
    g.link(("SetSpecific", "then"), ("SetLive", "execute"))
    g.link(("GetDock", "Dock"), ("SetLive", "self"))
    g.link(("MakeEmpty", "ResourceCollection"), ("SetLive", "m_requiredEmbarkSupplies_live"))

    get_member(g, "InputGet", WORKDOCK, "m_inputStockpile", STRUCT(STOCKPILE), 750, 300)
    g.link(("GetDock", "Dock"), ("InputGet", "self"))
    break_struct(g, "InputBreak", STOCKPILE, [("Slots", MAP_SLOTS)], 1000, 300)
    g.link(("InputGet", "m_inputStockpile"), ("InputBreak", "Stockpile"))
    set_local(g, "SetSlots", F, "Slots", MAP_SLOTS, 750, 0)
    g.link(("SetLive", "then"), ("SetSlots", "execute"))
    g.link(("InputBreak", "Slots"), ("SetSlots", "Slots"))
    g.call("SlotKeys", MAPLIB, "Map_Keys", 1000, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", MAP_SLOTS, None), ("Keys", "out", NAME_ARRAY, None)])
    g.link(("GetSlots", "Slots"), ("SlotKeys", "TargetMap"))
    g.link(("SetSlots", "then"), ("SlotKeys", "execute"))
    for_each(g, "ForKeys", NAME, 1250, 0)
    g.link(("SlotKeys", "then"), ("ForKeys", "Exec"))
    g.link(("SlotKeys", "Keys"), ("ForKeys", "Array"))

    key = ("ForKeys", "Array Element")
    map_find(g, "SlotFind", ("GetSlots", "Slots"), key, MAP_SLOTS, STRUCT(SLOT), 1500, 300)
    set_local(g, "SetSlot", F, "Slot", STRUCT(SLOT), 1500, 0)
    g.link(("ForKeys", "LoopBody"), ("SetSlot", "execute"))
    g.link(("SlotFind", "Value"), ("SetSlot", "Slot"))
    set_fields(g, "ZeroCapacity", SLOT, "capacity", INT, 1750, 0)
    g.link(("SetSlot", "then"), ("ZeroCapacity", "execute"))
    g.link(("GetSlot", "Slot"), ("ZeroCapacity", "StructRef"))
    map_add(g, "PutSlot", ("GetSlots", "Slots"), key, ("ZeroCapacity", "StructOut"), MAP_SLOTS, STRUCT(SLOT), 2000, 0)
    g.link(("ZeroCapacity", "then"), ("PutSlot", "execute"))

    make_struct(g, "MakeInput", STOCKPILE, [("Slots", MAP_SLOTS)], 1500, -350)
    g.link(("GetSlots", "Slots"), ("MakeInput", "Slots"))
    set_member(g, "InputSet", WORKDOCK, "m_inputStockpile", STRUCT(STOCKPILE), 1750, -350)
    g.link(("ForKeys", "Completed"), ("InputSet", "execute"))
    g.link(("GetDock", "Dock"), ("InputSet", "self"))
    g.link(("MakeInput", "Stockpile"), ("InputSet", "m_inputStockpile"))
    return g.render()


def req_key(g, p, id_src, name_src, x, y):
    """ "<dock id>|<resource>" - one entry of the Requested set."""
    g.call(p + "IdStr", STRLIB, "Conv_IntToString", x, y,
           [("InInt", "in", INT, None), ("ReturnValue", "out", STR, None)])
    g.link(id_src, (p + "IdStr", "InInt"))
    g.call(p + "Sep", STRLIB, "Concat_StrStr", x + 250, y,
           [("A", "in", STR, None), ("B", "in", STR, 'DefaultValue="|"'), ("ReturnValue", "out", STR, None)])
    g.link((p + "IdStr", "ReturnValue"), (p + "Sep", "A"))
    if name_src is None:
        return (p + "Sep", "ReturnValue")
    g.call(p + "ResStr", STRLIB, "Conv_NameToString", x, y + 100,
           [("InName", "in", NAME, None), ("ReturnValue", "out", STR, None)])
    g.link(name_src, (p + "ResStr", "InName"))
    g.call(p + "Full", STRLIB, "Concat_StrStr", x + 500, y,
           [("A", "in", STR, None), ("B", "in", STR, None), ("ReturnValue", "out", STR, None)])
    g.link((p + "Sep", "ReturnValue"), (p + "Full", "A"))
    g.link((p + "ResStr", "ReturnValue"), (p + "Full", "B"))
    return (p + "Full", "ReturnValue")


def record_requested():
    """Add every resource in the dock's current request to Requested ("<id>|<resource>")."""
    g = Graph()
    F = "RecordRequested"
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    get_self(g, "GetRequested", "Requested", STR_SET, 0, 400)
    get_member(g, "Spec", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), 0, 500)
    g.link(("GetDock", "Dock"), ("Spec", "self"))
    break_struct(g, "BreakSpec", RESCOLL, [("counts", MAP_NAME_INT)], 250, 500)
    g.link(("Spec", "m_requiredEmbarkSupplies_dockSpecific"), ("BreakSpec", "ResourceCollection"))
    map_keys(g, "SpecKeys", ("BreakSpec", "counts"), MAP_NAME_INT, 0, 0)
    for_each(g, "ForKeys", NAME, 250, 0)
    g.link(("SpecKeys", "then"), ("ForKeys", "Exec"))
    g.link(("SpecKeys", "Keys"), ("ForKeys", "Array"))
    k = req_key(g, "K", dock_id_call(g, "DockId", ("GetDock", "Dock"), 500, 300), ("ForKeys", "Array Element"), 750, 300)
    g.call("Add", SETLIB, "Set_Add", 550, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetSet", "in", STR_SET, None), ("NewItem", "in", STR, None)])
    g.link(("ForKeys", "LoopBody"), ("Add", "execute"))
    g.link(("GetRequested", "Requested"), ("Add", "TargetSet"))
    g.link(k, ("Add", "NewItem"))
    return g.render()


def clear_requested():
    """Remove a dock's entries ("<id>|...") from Requested."""
    g = Graph()
    F = "ClearRequested"
    get_local(g, "GetId", F, "Id", INT, 0, 300)
    get_self(g, "GetRequested", "Requested", STR_SET, 0, 400)
    g.call("ToArray", SETLIB, "Set_ToArray", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("A", "in", STR_SET, None), ("Result", "out", STR_ARRAY, None)])
    g.link(("GetRequested", "Requested"), ("ToArray", "A"))
    for_each(g, "ForEntries", STR, 250, 0)
    g.link(("ToArray", "then"), ("ForEntries", "Exec"))
    g.link(("ToArray", "Result"), ("ForEntries", "Array"))
    prefix = req_key(g, "P", ("GetId", "Id"), None, 250, 300)
    g.call("Mine", STRLIB, "StartsWith", 750, 300,
           [("SourceString", "in", STR, None), ("InPrefix", "in", STR, None),
            ("SearchCase", "in", SEARCHCASE_PIN, 'DefaultValue="IgnoreCase"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("ForEntries", "Array Element"), ("Mine", "SourceString"))
    g.link(prefix, ("Mine", "InPrefix"))
    branch(g, "BrMine", 550, 0)
    g.link(("ForEntries", "LoopBody"), ("BrMine", "execute"))
    g.link(("Mine", "ReturnValue"), ("BrMine", "Condition"))
    g.call("Remove", SETLIB, "Set_Remove", 800, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetSet", "in", STR_SET, None), ("Item", "in", STR, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("BrMine", "then"), ("Remove", "execute"))
    g.link(("GetRequested", "Requested"), ("Remove", "TargetSet"))
    g.link(("ForEntries", "Array Element"), ("Remove", "Item"))
    return g.render()


def freight_counts():
    """Units in the ship's hold of resources this dock was asked to load (Requested); provisions etc. excluded."""
    g = Graph()
    F = "FreightCounts"
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 400)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 500)
    get_local(g, "GetPartnerIn", F, "Partner", OBJ(WORKDOCK), 0, 550)
    get_self(g, "GetRequested", "Requested", STR_SET, 0, 600)
    get_local(g, "GetHold", F, "Hold", MAP_NAME_INT, 0, 700)
    get_local(g, "GetSum", F, "Sum", INT, 0, 800)
    g.node("ZeroSum", K2 + "K2Node_VariableSet", [local_var(F, "Sum")], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Sum", "in", INT, 'DefaultValue="0"'), ("Output_Get", "out", INT, None)])
    user_call(g, "Deficits", "DeficitsFor", 250, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Want", STRUCT(RESCOLL))])
    g.link(("ZeroSum", "then"), ("Deficits", "execute"))
    g.link(("GetPartnerIn", "Partner"), ("Deficits", "Dock"))
    break_struct(g, "BreakWant", RESCOLL, [("counts", MAP_NAME_INT)], 500, 250)
    g.link(("Deficits", "Want"), ("BreakWant", "ResourceCollection"))
    set_local(g, "SetWant", F, "Want", MAP_NAME_INT, 500, 0)
    g.link(("Deficits", "then"), ("SetWant", "execute"))
    g.link(("BreakWant", "counts"), ("SetWant", "Want"))
    user_call(g, "HoldC", "HoldCounts", 750, 0, ins=[("Ship", OBJ(SHIP))], outs=[("Counts", MAP_NAME_INT), ("Total", INT)])
    g.link(("SetWant", "then"), ("HoldC", "execute"))
    g.link(("GetShip", "Ship"), ("HoldC", "Ship"))
    set_local(g, "SetHold", F, "Hold", MAP_NAME_INT, 1000, 0)
    g.link(("HoldC", "then"), ("SetHold", "execute"))
    g.link(("HoldC", "Counts"), ("SetHold", "Hold"))
    map_keys(g, "HoldKeys", ("GetHold", "Hold"), MAP_NAME_INT, 1250, 0)
    g.link(("SetHold", "then"), ("HoldKeys", "execute"))
    for_each(g, "ForKeys", NAME, 1500, 0)
    g.link(("HoldKeys", "then"), ("ForKeys", "Exec"))
    g.link(("HoldKeys", "Keys"), ("ForKeys", "Array"))
    key = ("ForKeys", "Array Element")
    k = req_key(g, "K", dock_id_call(g, "DockId", ("GetDock", "Dock"), 1500, 400), key, 1750, 400)
    g.call("Wanted", SETLIB, "Set_Contains", 2500, 250,
           [("TargetSet", "in", STR_SET, None), ("ItemToFind", "in", STR, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetRequested", "Requested"), ("Wanted", "TargetSet"))
    g.link(k, ("Wanted", "ItemToFind"))
    # ... or currently wanted by the partner (recognises freight again after a reload)
    get_local(g, "GetWant", F, "Want", MAP_NAME_INT, 0, 1000)
    partner_want = map_contains(g, "PartnerWants", ("GetWant", "Want"), key, MAP_NAME_INT, 2500, 400, key_type=NAME)
    g.call("FreightKey", MATHLIB, "BooleanOR", 2750, 300,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Wanted", "ReturnValue"), ("FreightKey", "A"))
    g.link(partner_want, ("FreightKey", "B"))
    wanted = ("FreightKey", "ReturnValue")
    branch(g, "BrWanted", 1800, 0)
    g.link(("ForKeys", "LoopBody"), ("BrWanted", "execute"))
    g.link(wanted, ("BrWanted", "Condition"))
    map_find(g, "Qty", ("GetHold", "Hold"), key, MAP_NAME_INT, INT, 2050, 250)
    total = int_op(g, "SumPlus", "Add_IntInt", ("GetSum", "Sum"), ("Qty", "Value"), 2300, 250)
    set_local(g, "SetSum", F, "Sum", INT, 2050, 0)
    g.link(("BrWanted", "then"), ("SetSum", "execute"))
    g.link(total, ("SetSum", "Sum"))
    get_local(g, "GetSumForReturn", F, "Sum", INT, 1500, -200)
    return g.render()


SPECS = {
    "DeficitsFor": fn_spec(("ClearCounts", "execute"), inputs=[("Dock", OBJ(WORKDOCK))],
                           outputs=[("Want", STRUCT(RESCOLL))],
                           locals_=[("Counts", MAP_NAME_INT), ("Linker", OBJ(LINKER)), ("Deficit", MAP_NAME_INT)],
                           returns=[("ForIds", "Completed")], values=[("MakeWant", "ResourceCollection", "Want")]),
    "KeepEmptyDeficits": fn_spec(("ClearResult", "execute"), inputs=[("Storage", OBJ(RESBUILDING))],
                                 outputs=[("Deficit", MAP_NAME_INT)],
                                 locals_=[("Result", MAP_NAME_INT), ("Inbound", MAP_NAME_INT),
                                          ("Slots", MAP_NAME_TO(SLOT)), ("Need", INT)],
                                 returns=[("ForKeys", "Completed")], values=[("GetResultForReturn", "Result", "Deficit")]),
    "RequestFor": fn_spec(("SetOld", "execute"), inputs=[("Dock", OBJ(WORKDOCK)), ("Want", STRUCT(RESCOLL))],
                          locals_=[("Live", MAP_NAME_INT), ("Slots", MAP_NAME_TO(SLOT)), ("Slot", STRUCT(SLOT)),
                                   ("Old", MAP_NAME_INT)]),
    "UpdateRequest": fn_spec(("Plan", "execute"),
                             inputs=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP)),
                                     ("NoMore", BOOL)],
                             outputs=[("Remaining", INT), ("InFlight", INT)],
                             locals_=[],
                             returns=[("LogReq", "then"), ("BrChanged", "else")],
                             values=[("Plan", "Remaining", "Remaining"), ("Plan", "InFlight", "InFlight")]),
    "FreightTick": fn_spec(("Refresh", "execute"),
                           locals_=[("Partner", OBJ(WORKDOCK)), ("Id", INT), ("Ship", OBJ(SHIP)), ("Remaining", INT),
                                    ("Loaded", INT), ("Now", DOUBLE), ("Freight", INT), ("InFlight", INT),
                                    ("Reason", STR)]),
}


GRAPHS = {
    "DeficitsFor": deficits_for,
    "KeepEmptyDeficits": keep_empty_deficits,
    "RequestFor": request_for,
    "TransferFrom": transfer_from,
    "HoldCounts": hold_counts,
    "UpdateRequest": update_request,
    "FreightTick": freight_tick,
    "PauseLoading": pause_loading,
    "FreightCounts": freight_counts,
    "RecordRequested": record_requested,
    "ClearRequested": clear_requested,
}
