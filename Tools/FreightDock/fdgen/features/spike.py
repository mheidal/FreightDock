"""TEMPORARY - persistence spike for many-to-many links (Docs/FreightDock/Many-to-many links.md): checks that a
packed value in activeTradePartnerId survives save/load. Leave this module out when merging into freightdock:
remove it from registry.MODULES, the SpikeTick hook in options.pair_key_tick, and the SpikeFrames variable.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import BOOL, EXEC, INT, OBJ
from fdgen.core.paths import K2, MATHLIB, MODAPI, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    bop, branch, for_each, get_local, get_member, get_self, int_op, is_valid, set_local,
    set_self, user_call)
from fdgen.core.text import fmt_to_string, log_msg
from fdgen.features.docks import dock_id_call, is_freight_call
from fdgen.features.pairing import set_partner


SPIKE_VALUE = str(-(2 + (5 | 7 << 6 | 9 << 12 | 33 << 18 | 62 << 24)))  # own slot 5, links 7, 9, 33, 62


def spike_storage():
    """SpikeStorage (temporary, once ~2 s after load): does a packed value in a freight dock's activeTradePartnerId
    survive a save? Logs every freight dock's value; if one holds SPIKE_VALUE, says so; otherwise writes SPIKE_VALUE
    to the first unpaired (-1) freight dock. Locals: Target (Work Dock), Found (Boolean)."""
    g = Graph()
    F = "SpikeStorage"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 400)
    get_self(g, "GetDocks", "Docks", OBJ(WORKDOCK, "Array"), 0, 500)
    get_local(g, "GetTarget", F, "Target", OBJ(WORKDOCK), 0, 600)
    get_local(g, "GetFound", F, "Found", BOOL, 0, 700)
    for_each(g, "ForDocks", OBJ(WORKDOCK), 0, 0)
    g.link(("GetDocks", "Docks"), ("ForDocks", "Array"))
    d = ("ForDocks", "Array Element")
    branch(g, "BrFreight", 250, 0)
    g.link(("ForDocks", "LoopBody"), ("BrFreight", "execute"))
    g.link(is_freight_call(g, "IsFreight", d, 250, 300), ("BrFreight", "Condition"))
    get_member(g, "Val", WORKDOCK, "activeTradePartnerId", INT, 250, 450)
    g.link(d, ("Val", "self"))
    v = ("Val", "activeTradePartnerId")
    sl = fmt_to_string(g, "FmtDock", "Packed spike: freight dock {d} value {v}", [("d", INT), ("v", INT)], 500, 600)
    g.link(dock_id_call(g, "DockId", d, 250, 600), ("FmtDock", "d"))
    g.link(v, ("FmtDock", "v"))
    log_msg(g, "LogDock", "GetModAPI", 500, 0)
    g.link(("BrFreight", "then"), ("LogDock", "execute"))
    g.link((sl, "ReturnValue"), ("LogDock", "Msg"))
    branch(g, "BrIsTest", 750, 0)
    g.link(("LogDock", "then"), ("BrIsTest", "execute"))
    g.link(int_op(g, "IsTest", "EqualEqual_IntInt", v, None, 750, 450, b_default=SPIKE_VALUE), ("BrIsTest", "Condition"))
    g.node("SetFound", K2 + "K2Node_VariableSet", [local_var(F, "Found")], 1000, -100,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Found", "in", BOOL, 'DefaultValue="true"'),
            ("Output_Get", "out", BOOL, None)])
    g.link(("BrIsTest", "then"), ("SetFound", "execute"))
    is_valid(g, "TargetOk", WORKDOCK, 1000, 450)
    g.link(("GetTarget", "Target"), ("TargetOk", "Object"))
    g.call("NoTarget", MATHLIB, "Not_PreBool", 1250, 450, [("A", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("TargetOk", "ReturnValue"), ("NoTarget", "A"))
    free = bop(g, "Free", "BooleanAND", int_op(g, "Unpaired", "EqualEqual_IntInt", v, None, 1000, 600, b_default="-1"),
               ("NoTarget", "ReturnValue"), 1250, 600)
    branch(g, "BrFree", 1000, 100)
    g.link(("BrIsTest", "else"), ("BrFree", "execute"))
    g.link(free, ("BrFree", "Condition"))
    set_local(g, "SetTarget", F, "Target", OBJ(WORKDOCK), 1250, 100)
    g.link(("BrFree", "then"), ("SetTarget", "execute"))
    g.link(d, ("SetTarget", "Target"))

    branch(g, "BrFound", 250, -300)
    g.link(("ForDocks", "Completed"), ("BrFound", "execute"))
    g.link(("GetFound", "Found"), ("BrFound", "Condition"))
    log_msg(g, "LogFound", "GetModAPI", 500, -450, literal="Packed spike: test value FOUND after load")
    g.link(("BrFound", "then"), ("LogFound", "execute"))
    branch(g, "BrHaveTarget", 500, -300)
    g.link(("BrFound", "else"), ("BrHaveTarget", "execute"))
    g.link(("TargetOk", "ReturnValue"), ("BrHaveTarget", "Condition"))
    set_partner(g, "Write", 750, -300, literal=SPIKE_VALUE)
    g.link(("BrHaveTarget", "then"), ("Write", "execute"))
    g.link(("GetTarget", "Target"), ("Write", "self"))
    sw = fmt_to_string(g, "FmtWrote", "Packed spike: wrote test value to unpaired freight dock {d} - save, reload, check", [("d", INT)], 1000, -150)
    g.link(dock_id_call(g, "TargetId", ("GetTarget", "Target"), 750, -150), ("FmtWrote", "d"))
    log_msg(g, "LogWrote", "GetModAPI", 1000, -300)
    g.link(("Write", "then"), ("LogWrote", "execute"))
    g.link((sw, "ReturnValue"), ("LogWrote", "Msg"))
    log_msg(g, "LogNoTarget", "GetModAPI", 750, -450, literal="Packed spike: no test value and no unpaired freight dock")
    g.link(("BrHaveTarget", "else"), ("LogNoTarget", "execute"))
    return g.render()


def spike_tick():
    """SpikeTick (temporary, from PairKeyTick): SpikeStorage once, 120 frames after load (SpikeFrames)."""
    g = Graph()
    get_self(g, "GetFrames", "SpikeFrames", INT, 0, 400)
    set_self(g, "Count", "SpikeFrames", INT, 0, 0)
    g.link(int_op(g, "Plus1", "Add_IntInt", ("GetFrames", "SpikeFrames"), None, 0, 550, b_default="1"), ("Count", "SpikeFrames"))
    branch(g, "BrDue", 250, 0)
    g.link(("Count", "then"), ("BrDue", "execute"))
    g.link(int_op(g, "Due", "EqualEqual_IntInt", ("GetFrames", "SpikeFrames"), None, 250, 400, b_default="120"), ("BrDue", "Condition"))
    user_call(g, "Spike", "SpikeStorage", 500, 0)
    g.link(("BrDue", "then"), ("Spike", "execute"))
    return g.render()


SPECS = {
    "SpikeStorage": fn_spec(("ForDocks", "Exec"), locals_=[("Target", OBJ(WORKDOCK)), ("Found", BOOL, "false")]),
    "SpikeTick": fn_spec(("Count", "execute")),
}


GRAPHS = {
    "SpikeStorage": spike_storage,
    "SpikeTick": spike_tick,
}
