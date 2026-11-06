"""Stevedore modifier: +10 carry capacity for workers at a freight dock. RegisterExtras (BP_Startup) adds the
modifier (in Loom, BPL_FDSetup); SetStevedore / SyncStevedores apply it in BP_MapLoad.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, EXEC, INT, MOD_MAP, NAME, OBJ, SLOT_ARRAY, STR, STRUCT, T
from fdgen.core.paths import (
    SETUP_LIB, AGENT, AGENTMOD, AGENTSTATE, K2, MAPLIB, MATHLIB, MODAPI, MODSTATE, SYSLIB, WORKDOCK,
    WORKERS, WORKERSLOT)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    arrfn, bnot, bop, branch, break_struct, for_each, get_local, get_member, get_self,
    is_valid, set_fields, set_local, set_member, set_pin_default, set_self, user_call)
from fdgen.core.text import LOG_PREFIX, concat_parts, log_msg, to_str


STEVEDORE = "mod.stevedore"


def register_extras():
    """RegisterExtras (BP_Startup): BPL_FDSetup.RegisterExtras(ModAPI) - the Stevedore worker modifier (AgentModifiers
    row, copied from mod.constructionyardWorker, carry +10, no expiry). Its strings are in BPL_FDText."""
    g = Graph()
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 250)
    g.call("Call", SETUP_LIB, "RegisterExtras", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Api", "in", OBJ(MODAPI), None)])
    g.link(("GetModAPI", "ModAPI"), ("Call", "Api"))
    return g.render()


def set_stevedore():
    """SetStevedore(Agent, On): add or remove the Stevedore modifier in the worker's active modifiers (the game's own
    data, made writable through Suzie), logging the change with the worker's carry capacity.
    Locals: State (AgentState), ModState (AgentModifierState), Mods (Name -> AgentModifier map), Mod (AgentModifier)."""
    g = Graph()
    F = "SetStevedore"
    get_local(g, "GetAgent", F, "Agent", OBJ(AGENT), 0, 400)
    get_local(g, "GetOn", F, "On", BOOL, 0, 500)
    get_local(g, "GetState", F, "State", STRUCT(AGENTSTATE), 0, 600)
    get_local(g, "GetModState", F, "ModState", STRUCT(MODSTATE), 0, 700)
    get_local(g, "GetMods", F, "Mods", MOD_MAP, 0, 800)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 1000)
    agent = ("GetAgent", "Agent")
    # copy the state down to the modifier map
    get_member(g, "AgentState", AGENT, "m_state", STRUCT(AGENTSTATE), 250, 400)
    g.link(agent, ("AgentState", "self"))
    set_local(g, "SetState", F, "State", STRUCT(AGENTSTATE), 0, 0)
    g.link(("AgentState", "m_state"), ("SetState", "State"))
    break_struct(g, "BreakState", AGENTSTATE, [("modifierState", STRUCT(MODSTATE)), ("derived_carryCapacity", INT)], 250, 600)
    g.link(("GetState", "State"), ("BreakState", "AgentState"))
    set_local(g, "SetModState", F, "ModState", STRUCT(MODSTATE), 250, 0)
    g.link(("SetState", "then"), ("SetModState", "execute"))
    g.link(("BreakState", "modifierState"), ("SetModState", "ModState"))
    break_struct(g, "BreakMods", MODSTATE, [("activeModifiers_all", MOD_MAP)], 500, 700)
    g.link(("GetModState", "ModState"), ("BreakMods", "AgentModifierState"))
    set_local(g, "SetMods", F, "Mods", MOD_MAP, 500, 0)
    g.link(("SetModState", "then"), ("SetMods", "execute"))
    g.link(("BreakMods", "activeModifiers_all"), ("SetMods", "Mods"))
    g.call("Has", MAPLIB, "Map_Contains", 750, 300,
           [("TargetMap", "in", MOD_MAP, None), ("Key", "in", NAME, f'DefaultValue="{STEVEDORE}"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetMods", "Mods"), ("Has", "TargetMap"))
    g.call("Same", MATHLIB, "EqualEqual_BoolBool", 1000, 300,
           [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("Has", "ReturnValue"), ("Same", "A"))
    g.link(("GetOn", "On"), ("Same", "B"))
    branch(g, "BrChange", 750, 0)
    g.link(("SetMods", "then"), ("BrChange", "execute"))
    g.link(bnot(g, "Changes", ("Same", "ReturnValue"), 1250, 300), ("BrChange", "Condition"))
    branch(g, "BrOn", 1000, 0)
    g.link(("BrChange", "then"), ("BrOn", "execute"))
    g.link(("GetOn", "On"), ("BrOn", "Condition"))
    # on: the modifier as registered in AgentModifiers
    g.call("Lookup", "/Script/CoreUObject.Class'/Script/ProjectArco.ArcoGameInstance'", "GetAgentModifier", 1250, -150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Context", "in", OBJ("/Script/CoreUObject.Object"), None), ("out_modifier", "out", STRUCT(AGENTMOD), None),
            ("Key", "in", NAME, f'DefaultValue="{STEVEDORE}"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("BrOn", "then"), ("Lookup", "execute"))
    g.node("Self", K2 + "K2Node_Self", [], 1000, -300, [("self", "out", ['PinType.PinCategory="object"', 'PinType.PinSubCategory="self"'], None)])
    g.link(("Self", "self"), ("Lookup", "Context"))
    g.call("Add", MAPLIB, "Map_Add", 1500, -150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MOD_MAP, None),
            ("Key", "in", NAME, f'DefaultValue="{STEVEDORE}"'), ("Value", "in", STRUCT(AGENTMOD), None)])
    g.link(("Lookup", "then"), ("Add", "execute"))
    g.link(("GetMods", "Mods"), ("Add", "TargetMap"))
    g.link(("Lookup", "out_modifier"), ("Add", "Value"))
    g.call("Remove", MAPLIB, "Map_Remove", 1250, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetMap", "in", MOD_MAP, None),
            ("Key", "in", NAME, f'DefaultValue="{STEVEDORE}"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetMods", "Mods"), ("Remove", "TargetMap"))
    g.link(("BrOn", "else"), ("Remove", "execute"))
    # write back: map -> modifier state -> agent state -> agent
    set_fields(g, "PutMods", MODSTATE, "activeModifiers_all", MOD_MAP, 1750, 0)
    g.link(("Add", "then"), ("PutMods", "execute"))
    g.link(("Remove", "then"), ("PutMods", "execute"))
    g.link(("GetModState", "ModState"), ("PutMods", "StructRef"))
    g.link(("GetMods", "Mods"), ("PutMods", "activeModifiers_all"))
    set_fields(g, "PutModState", AGENTSTATE, "modifierState", STRUCT(MODSTATE), 2000, 0)
    g.link(("PutMods", "then"), ("PutModState", "execute"))
    g.link(("GetState", "State"), ("PutModState", "StructRef"))
    g.link(("PutMods", "StructOut"), ("PutModState", "modifierState"))
    set_member(g, "PutState", AGENT, "m_state", STRUCT(AGENTSTATE), 2250, 0)
    g.link(("PutModState", "then"), ("PutState", "execute"))
    g.link(agent, ("PutState", "self"))
    g.link(("PutModState", "StructOut"), ("PutState", "m_state"))
    # log: who, on/off, found in the table, carry capacity as the game had it
    OBJT = OBJ("/Script/CoreUObject.Object")
    parts = ["Stevedore ", to_str(g, "SOn", "Conv_BoolToString", "InBool", BOOL, ("GetOn", "On"), 1750, 500), ": ",
             to_str(g, "SName", "GetDisplayName", "Object", OBJT, agent, 2000, 500, lib=SYSLIB),
             " (modifier found: ", to_str(g, "SFound", "Conv_BoolToString", "InBool", BOOL, ("Lookup", "ReturnValue"), 2250, 500),
             ", carry capacity ", to_str(g, "SCarry", "Conv_IntToString", "InInt", INT, ("BreakState", "derived_carryCapacity"), 2500, 500), ")"]
    msg = concat_parts(g, "Msg", parts, 1750, 700)
    log_msg(g, "LogChange", "GetModAPI", 2500, 0)
    g.link(("PutState", "then"), ("LogChange", "execute"))
    g.link((msg, "ReturnValue"), ("LogChange", "Msg"))
    return g.render()


def sync_stevedores():
    """SyncStevedores (after each FreightTick): every worker in a freight dock's worker slots has the Stevedore
    modifier, and anyone in Stevedores who no longer works at one loses it.
    Local: Current (Agent array)."""
    g = Graph()
    F = "SyncStevedores"
    get_self(g, "GetDocks", "Docks", OBJ(WORKDOCK, "Array"), 0, 400)
    get_self(g, "GetStevedores", "Stevedores", OBJ(AGENT, "Array"), 0, 500)
    get_local(g, "GetCurrent", F, "Current", OBJ(AGENT, "Array"), 0, 600)
    arrfn(g, "ClearCurrent", "Array_Clear", 0, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", OBJ(AGENT, "Array"), None)])
    g.link(("GetCurrent", "Current"), ("ClearCurrent", "TargetArray"))
    for_each(g, "ForDocks", OBJ(WORKDOCK), 250, 0)
    g.link(("ClearCurrent", "then"), ("ForDocks", "Exec"))
    g.link(("GetDocks", "Docks"), ("ForDocks", "Array"))
    get_member(g, "Workers", WORKDOCK, "m_workers", STRUCT(WORKERS), 250, 300)
    g.link(("ForDocks", "Array Element"), ("Workers", "self"))
    break_struct(g, "BreakWorkers", WORKERS, [("m_workerSlots", SLOT_ARRAY)], 500, 300)
    g.link(("Workers", "m_workers"), ("BreakWorkers", "WorkerAssignment"))
    for_each(g, "ForSlots", STRUCT(WORKERSLOT), 500, 0)
    g.link(("ForDocks", "LoopBody"), ("ForSlots", "Exec"))
    g.link(("BreakWorkers", "m_workerSlots"), ("ForSlots", "Array"))
    break_struct(g, "BreakSlot", WORKERSLOT, [("Agent", OBJ(AGENT))], 750, 300)
    g.link(("ForSlots", "Array Element"), ("BreakSlot", "WorkerSlot"))
    is_valid(g, "HasAgent", AGENT, 1000, 300)
    g.link(("BreakSlot", "Agent"), ("HasAgent", "Object"))
    branch(g, "BrAgent", 750, 0)
    g.link(("ForSlots", "LoopBody"), ("BrAgent", "execute"))
    g.link(("HasAgent", "ReturnValue"), ("BrAgent", "Condition"))
    arrfn(g, "Keep", "Array_AddUnique", 1000, 0,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", OBJ(AGENT, "Array"), None),
           ("NewItem", "in", OBJ(AGENT), None), ("ReturnValue", "out", INT, None)])
    g.link(("BrAgent", "then"), ("Keep", "execute"))
    g.link(("GetCurrent", "Current"), ("Keep", "TargetArray"))
    g.link(("BreakSlot", "Agent"), ("Keep", "NewItem"))
    user_call(g, "On", "SetStevedore", 1250, 0, ins=[("Agent", OBJ(AGENT)), ("On", BOOL)])
    g.link(("Keep", "then"), ("On", "execute"))
    g.link(("BreakSlot", "Agent"), ("On", "Agent"))
    set_pin_default(g, "On", "On", "true")
    # those who left
    for_each(g, "ForOld", OBJ(AGENT), 500, -300)
    g.link(("ForDocks", "Completed"), ("ForOld", "Exec"))
    g.link(("GetStevedores", "Stevedores"), ("ForOld", "Array"))
    arrfn(g, "Still", "Array_Contains", 750, -150,
          [("TargetArray", "in", OBJ(AGENT, "Array"), None), ("ItemToFind", "in", OBJ(AGENT), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetCurrent", "Current"), ("Still", "TargetArray"))
    g.link(("ForOld", "Array Element"), ("Still", "ItemToFind"))
    is_valid(g, "OldOk", AGENT, 750, -50)
    g.link(("ForOld", "Array Element"), ("OldOk", "Object"))
    branch(g, "BrLeft", 750, -300)
    g.link(("ForOld", "LoopBody"), ("BrLeft", "execute"))
    g.link(bop(g, "Left", "BooleanAND", ("OldOk", "ReturnValue"), bnot(g, "NotStill", ("Still", "ReturnValue"), 1000, -150), 1250, -100),
           ("BrLeft", "Condition"))
    user_call(g, "Off", "SetStevedore", 1000, -300, ins=[("Agent", OBJ(AGENT)), ("On", BOOL)])
    g.link(("BrLeft", "then"), ("Off", "execute"))
    g.link(("ForOld", "Array Element"), ("Off", "Agent"))
    set_pin_default(g, "Off", "On", "false")
    set_self(g, "Remember", "Stevedores", OBJ(AGENT, "Array"), 750, -500)
    g.link(("ForOld", "Completed"), ("Remember", "execute"))
    g.link(("GetCurrent", "Current"), ("Remember", "Stevedores"))
    return g.render()


SPECS = {
    "RegisterExtras": fn_spec(("Call", "execute")),
    "SetStevedore": fn_spec(("SetState", "execute"), inputs=[("Agent", OBJ(AGENT)), ("On", BOOL)],
                            locals_=[("State", STRUCT(AGENTSTATE)), ("ModState", STRUCT(MODSTATE)), ("Mods", MOD_MAP),
                                     ("Mod", STRUCT(AGENTMOD))]),
    "SyncStevedores": fn_spec(("ClearCurrent", "execute"), locals_=[("Current", OBJ(AGENT, "Array"))]),
}


GRAPHS = {
    "RegisterExtras": register_extras,
    "SetStevedore": set_stevedore,
    "SyncStevedores": sync_stevedores,
}
