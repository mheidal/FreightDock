"""Loading: what the partner island needs (DeficitsFor, RequestFor), what is held and requested, moving goods from
a stockpile into the ship (TransferFrom), and FreightTick, which decides when a loaded ship departs.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import (
    BOOL, DOUBLE, EXEC, INT, INT_ARRAY, INT_SET, MAP_INT_ACTOR, MAP_INT_DOUBLE,
    MAP_NAME_INT, MAP_NAME_TO, NAME, NAME_ARRAY, OBJ, SEARCHCASE_PIN, STR, STR_ARRAY, STR_SET, STRUCT)
from fdgen.core.paths import (
    CARGO, GRIDACTOR, ITEM, K2, LINKER, MAPLIB, MATHLIB, MODAPI, RESBUILDING, RESCOLL,
    SETLIB, SHIP, SHIPCONFIG, SHIPSTATE, SLOT, STOCKPILE, STRLIB, SYSLIB, WORKDOCK)
from fdgen.core.nodes import (
    branch, break_struct, comp_owner, find_component, for_each, get_local, get_member,
    get_self, int_op, is_valid, make_struct, map_add, map_contains, map_find, map_keys, set_fields, set_local,
    set_member, user_call)
from fdgen.core.text import fmt_to_string, log_msg
from fdgen.features.docks import dock_id_call


def deficits_for():
    """Sum of unmet requests over the dock's 'unload to' warehouses."""
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
    g.call("GetDeficits", f"/Script/CoreUObject.Class'{RESBUILDING}'", "GetLogisticsDeficitsAsCollection", 1800, 300,
           [("self", "in", OBJ(RESBUILDING), None), ("ReturnValue", "out", STRUCT(RESCOLL), None)])
    g.link(storage, ("GetDeficits", "self"))
    break_struct(g, "BreakDeficits", RESCOLL, [("counts", MAP_NAME_INT)], 2050, 300)
    g.link(("GetDeficits", "ReturnValue"), ("BreakDeficits", "ResourceCollection"))
    set_local(g, "SetDeficit", F, "Deficit", MAP_NAME_INT, 1800, 0)
    g.link(("BrStorage", "then"), ("SetDeficit", "execute"))
    g.link(("BreakDeficits", "counts"), ("SetDeficit", "Deficit"))

    get_local(g, "GetDeficit", F, "Deficit", MAP_NAME_INT, 2050, 450)
    map_keys(g, "DeficitKeys", ("GetDeficit", "Deficit"), MAP_NAME_INT, 2050, 0)
    g.link(("SetDeficit", "then"), ("DeficitKeys", "execute"))
    for_each(g, "ForKeys", NAME, 2300, 0)
    g.link(("DeficitKeys", "then"), ("ForKeys", "Exec"))
    g.link(("DeficitKeys", "Keys"), ("ForKeys", "Array"))
    get_local(g, "GetCounts", F, "Counts", MAP_NAME_INT, 2300, 450)
    map_find(g, "HaveFind", ("GetCounts", "Counts"), ("ForKeys", "Array Element"), MAP_NAME_INT, INT, 2550, 300)
    map_find(g, "NeedFind", ("GetDeficit", "Deficit"), ("ForKeys", "Array Element"), MAP_NAME_INT, INT, 2550, 450)
    total = int_op(g, "Total", "Add_IntInt", ("HaveFind", "Value"), ("NeedFind", "Value"), 2800, 350)
    map_add(g, "AddCount", ("GetCounts", "Counts"), ("ForKeys", "Array Element"), total, MAP_NAME_INT, INT, 2800, 0)
    g.link(("ForKeys", "LoopBody"), ("AddCount", "execute"))

    make_struct(g, "MakeWant", RESCOLL, [("counts", MAP_NAME_INT)], 1000, -250)
    g.link(("GetCounts", "Counts"), ("MakeWant", "counts"))
    return g.render()


def request_for():
    """Put Want into the dock's dock-specific supplies, live requirement and input slots."""
    g = Graph()
    F = "RequestFor"
    MAP_SLOTS = MAP_NAME_TO(SLOT)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    get_local(g, "GetWant", F, "Want", STRUCT(RESCOLL), 0, 400)
    get_local(g, "GetLive", F, "Live", MAP_NAME_INT, 0, 500)
    get_local(g, "GetSlots", F, "Slots", MAP_SLOTS, 0, 600)
    get_local(g, "GetSlot", F, "Slot", STRUCT(SLOT), 0, 700)

    set_member(g, "SetSpecific", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), 0, 0)
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
    map_keys(g, "WantKeys", ("WantBreak", "counts"), MAP_NAME_INT, 750, 0)
    g.link(("SetSlots", "then"), ("WantKeys", "execute"))
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


def update_request():
    """Request = partner's deficits - what's in our hold - what already waits in the partner's dock cargo."""
    g = Graph()
    F = "UpdateRequest"
    MAP_SLOTS = MAP_NAME_TO(SLOT)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 300)
    get_local(g, "GetPartner", F, "Partner", OBJ(WORKDOCK), 0, 400)
    get_local(g, "GetShip", F, "Ship", OBJ(SHIP), 0, 500)
    get_local(g, "GetWant", F, "WantMap", MAP_NAME_INT, 0, 600)
    get_local(g, "GetHold", F, "Hold", MAP_NAME_INT, 0, 700)
    get_local(g, "GetResult", F, "Result", MAP_NAME_INT, 0, 800)
    get_local(g, "GetRemaining", F, "Left", INT, 0, 900)
    get_local(g, "GetNeed", F, "Need", INT, 0, 1000)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 1100)

    g.call("ClearResult", MAPLIB, "Map_Clear", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MAP_NAME_INT, None)])
    g.link(("GetResult", "Result"), ("ClearResult", "TargetMap"))
    g.node("ZeroRemaining", K2 + "K2Node_VariableSet", [local_var(F, "Left")], 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Left", "in", INT, 'DefaultValue="0"'), ("Output_Get", "out", INT, None)])
    g.link(("ClearResult", "then"), ("ZeroRemaining", "execute"))

    user_call(g, "Deficits", "DeficitsFor", 500, 0, ins=[("Dock", OBJ(WORKDOCK))], outs=[("Want", STRUCT(RESCOLL))])
    g.link(("ZeroRemaining", "then"), ("Deficits", "execute"))
    g.link(("GetPartner", "Partner"), ("Deficits", "Dock"))
    break_struct(g, "BreakWant", RESCOLL, [("counts", MAP_NAME_INT)], 750, 250)
    g.link(("Deficits", "Want"), ("BreakWant", "ResourceCollection"))
    set_local(g, "SetWant", F, "WantMap", MAP_NAME_INT, 750, 0)
    g.link(("Deficits", "then"), ("SetWant", "execute"))
    g.link(("BreakWant", "counts"), ("SetWant", "WantMap"))
    user_call(g, "Hold", "HoldCounts", 1000, 0, ins=[("Ship", OBJ(SHIP))],
              outs=[("Counts", MAP_NAME_INT), ("Total", INT)])
    g.link(("SetWant", "then"), ("Hold", "execute"))
    g.link(("GetShip", "Ship"), ("Hold", "Ship"))
    set_local(g, "SetHold", F, "Hold", MAP_NAME_INT, 1250, 0)
    g.link(("Hold", "then"), ("SetHold", "execute"))
    g.link(("Hold", "Counts"), ("SetHold", "Hold"))

    map_keys(g, "WantKeys", ("GetWant", "WantMap"), MAP_NAME_INT, 1500, 0)
    g.link(("SetHold", "then"), ("WantKeys", "execute"))
    for_each(g, "ForKeys", NAME, 1750, 0)
    g.link(("WantKeys", "then"), ("ForKeys", "Exec"))
    g.link(("WantKeys", "Keys"), ("ForKeys", "Array"))

    key = ("ForKeys", "Array Element")
    map_find(g, "WantFind", ("GetWant", "WantMap"), key, MAP_NAME_INT, INT, 2000, 250)
    map_find(g, "HoldFind", ("GetHold", "Hold"), key, MAP_NAME_INT, INT, 2000, 400)
    get_member(g, "SeaGet", WORKDOCK, "m_stockpile_goodsFromSea", STRUCT(STOCKPILE), 2000, 550)
    g.link(("GetPartner", "Partner"), ("SeaGet", "self"))
    break_struct(g, "SeaBreak", STOCKPILE, [("Slots", MAP_SLOTS)], 2250, 550)
    g.link(("SeaGet", "m_stockpile_goodsFromSea"), ("SeaBreak", "Stockpile"))
    map_find(g, "SeaFind", ("SeaBreak", "Slots"), key, MAP_SLOTS, STRUCT(SLOT), 2500, 550)
    break_struct(g, "SeaSlot", SLOT, [("count", INT)], 2750, 550)
    g.link(("SeaFind", "Value"), ("SeaSlot", "ResourceStockpileSlot"))
    a = int_op(g, "MinusHold", "Subtract_IntInt", ("WantFind", "Value"), ("HoldFind", "Value"), 2500, 300)
    need = int_op(g, "MinusSea", "Subtract_IntInt", a, ("SeaSlot", "count"), 3000, 400)
    set_local(g, "SetNeed", F, "Need", INT, 2000, 0)
    g.link(("ForKeys", "LoopBody"), ("SetNeed", "execute"))
    g.link(need, ("SetNeed", "Need"))
    positive = int_op(g, "NeedPositive", "Greater_IntInt", ("GetNeed", "Need"), None, 2250, 150, b_default="0")
    branch(g, "BrNeed", 2250, 0)
    g.link(("SetNeed", "then"), ("BrNeed", "execute"))
    g.link(positive, ("BrNeed", "Condition"))
    map_add(g, "AddResult", ("GetResult", "Result"), key, ("GetNeed", "Need"), MAP_NAME_INT, INT, 2500, 0)
    g.link(("BrNeed", "then"), ("AddResult", "execute"))
    more = int_op(g, "RemainingPlus", "Add_IntInt", ("GetRemaining", "Left"), ("GetNeed", "Need"), 2750, 150)
    set_local(g, "SetRemaining", F, "Left", INT, 2750, 0)
    g.link(("AddResult", "then"), ("SetRemaining", "execute"))
    g.link(more, ("SetRemaining", "Left"))

    # after the loop: only rewrite the dock's request if it changed
    make_struct(g, "MakeResult", RESCOLL, [("counts", MAP_NAME_INT)], 1750, -450)
    g.link(("GetResult", "Result"), ("MakeResult", "counts"))
    user_call(g, "NewStr", "CollectionToString", 2000, -450, ins=[("Collection", STRUCT(RESCOLL))],
              outs=[("Result", STR)], impure=False)
    g.link(("MakeResult", "ResourceCollection"), ("NewStr", "Collection"))
    get_member(g, "SpecGet", WORKDOCK, "m_requiredEmbarkSupplies_dockSpecific", STRUCT(RESCOLL), 1750, -600)
    g.link(("GetDock", "Dock"), ("SpecGet", "self"))
    user_call(g, "OldStr", "CollectionToString", 2000, -600, ins=[("Collection", STRUCT(RESCOLL))],
              outs=[("Result", STR)], impure=False)
    g.link(("SpecGet", "m_requiredEmbarkSupplies_dockSpecific"), ("OldStr", "Collection"))
    g.call("Changed", STRLIB, "NotEqual_StrStr", 2250, -500,
           [("A", "in", STR, None), ("B", "in", STR, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("NewStr", "Result"), ("Changed", "A"))
    g.link(("OldStr", "Result"), ("Changed", "B"))
    branch(g, "BrChanged", 2000, -300)
    g.link(("ForKeys", "Completed"), ("BrChanged", "execute"))
    g.link(("Changed", "ReturnValue"), ("BrChanged", "Condition"))
    user_call(g, "Request", "RequestFor", 2250, -300,
              ins=[("Dock", OBJ(WORKDOCK)), ("Want", STRUCT(RESCOLL))])
    g.link(("BrChanged", "then"), ("Request", "execute"))
    g.link(("GetDock", "Dock"), ("Request", "Dock"))
    g.link(("MakeResult", "ResourceCollection"), ("Request", "Want"))
    dock_id = dock_id_call(g, "DockId", ("GetDock", "Dock"), 2500, -600)
    s = fmt_to_string(g, "FmtReq", "Dock {d} request now: {req}", [("d", INT), ("req", STR)], 2750, -600)
    g.link(dock_id, ("FmtReq", "d"))
    g.link(("NewStr", "Result"), ("FmtReq", "req"))
    log_msg(g, "LogReq", "GetModAPI", 2500, -300)
    g.link(("Request", "then"), ("LogReq", "execute"))
    g.link((s, "ReturnValue"), ("LogReq", "Msg"))
    get_local(g, "GetRemainingForReturn", F, "Left", INT, 1750, -150)
    return g.render()


def freight_tick():
    """Rule c: depart when full / nothing left to request / max wait; deliver TripSeconds later."""
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
    user_call(g, "Update", "UpdateRequest", 2300, 400,
              ins=[("Dock", OBJ(WORKDOCK)), ("Partner", OBJ(WORKDOCK)), ("Ship", OBJ(SHIP))],
              outs=[("Remaining", INT)])
    g.link(dock, ("Update", "Dock"))
    g.link(("GetPartner", "Partner"), ("Update", "Partner"))
    g.link(("GetShip", "Ship"), ("Update", "Ship"))
    set_local(g, "SetRemaining", F, "Remaining", INT, 2550, 400)
    g.link(("Update", "then"), ("SetRemaining", "execute"))
    g.link(("Update", "Remaining"), ("SetRemaining", "Remaining"))
    user_call(g, "Hold", "HoldCounts", 2800, 400, ins=[("Ship", OBJ(SHIP))],
              outs=[("Counts", MAP_NAME_INT), ("Total", INT)])
    user_call(g, "Record", "RecordRequested", 2300, 250, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(dock, ("Record", "Dock"))
    g.link(("SetRemaining", "then"), ("Hold", "execute"))
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
    full = int_op(g, "Full", "GreaterEqual_IntInt", ("GetLoaded", "Loaded"), ("BreakConfig", "cargoLimit"), 4550, 600)
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
    branch(g, "BrDepart", 4300, 200)
    g.link(("BrClockRunning", "then"), ("BrDepart", "execute"))
    g.link(("StartClock", "then"), ("BrDepart", "execute"))
    g.link(("ShouldGo", "ReturnValue"), ("BrDepart", "Condition"))
    map_add(g, "Depart", DEPARTED, ("GetId", "Id"), ("GetNow", "Now"), MAP_INT_DOUBLE, DOUBLE, 4550, 200, key_type=INT)
    g.link(("BrDepart", "then"), ("Depart", "execute"))
    partner_id2 = dock_id_call(g, "PartnerId2", ("GetPartner", "Partner"), 4800, 0)
    s_dep = fmt_to_string(g, "FmtDepart", "Dock {d} departs for partner {p} with {n} aboard (still wanted: {r})",
                          [("d", INT), ("p", INT), ("n", INT), ("r", INT)], 5050, 0)
    g.link(("GetId", "Id"), ("FmtDepart", "d"))
    g.link(partner_id2, ("FmtDepart", "p"))
    g.link(("GetFreight", "Freight"), ("FmtDepart", "n"))
    g.link(("GetRemaining", "Remaining"), ("FmtDepart", "r"))
    log_msg(g, "LogDepart", "GetModAPI", 4800, 200)
    g.link(("Depart", "then"), ("LogDepart", "execute"))
    g.link((s_dep, "ReturnValue"), ("LogDepart", "Msg"))
    user_call(g, "Pause", "PauseLoading", 5050, 200, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(("LogDepart", "then"), ("Pause", "execute"))
    g.link(dock, ("Pause", "Dock"))
    user_call(g, "Voyage", "StartVoyage", 5550, 200,
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


GRAPHS = {
    "DeficitsFor": deficits_for,
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
