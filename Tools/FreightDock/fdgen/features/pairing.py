"""Pairing storage and the pairing key: activeTradePartnerId holds -2 - partnerId when paired (-1 = unpaired).
PartnerOf, Unpair, PairAtCursor (F5: select, pair, cancel, unpair).
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import BOOL, EXEC, INT, KEY, OBJ, STR, STRUCT, TEXT
from fdgen.core.paths import K2, MATHLIB, MODAPI, STRLIB, TEXTLIB, VECTOR, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    branch, clear_var, get_local, get_member, get_self, int_op, is_valid, member_of,
    self_var, set_local, user_call)
from fdgen.core.text import fmt_to_string, log_msg, toast
from fdgen.features.docks import dock_id_call, is_freight_call


def flip(g, name, src, x, y):
    """-2 - x: encodes a building ID as a partner value, and decodes it back."""
    g.call(name, MATHLIB, "Subtract_IntInt", x, y,
           [("A", "in", INT, 'DefaultValue="-2"'), ("B", "in", INT, None), ("ReturnValue", "out", INT, None)])
    g.link(src, (name, "B"))
    return (name, "ReturnValue")


def set_partner(g, name, x, y, literal=None):
    return g.node(name, K2 + "K2Node_VariableSet", [member_of(WORKDOCK, "activeTradePartnerId")], x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("self", "in", OBJ(WORKDOCK), None),
                   ("activeTradePartnerId", "in", INT, None if literal is None else f'DefaultValue="{literal}"'),
                   ("Output_Get", "out", INT, None)])


def unpair():
    g = Graph()
    F = "Unpair"
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 250)
    get_member(g, "Partner", WORKDOCK, "activeTradePartnerId", INT, 250, 250)
    g.link(("GetDock", "Dock"), ("Partner", "self"))
    g.call("IsPaired", MATHLIB, "LessEqual_IntInt", 500, 250,
           [("A", "in", INT, None), ("B", "in", INT, 'DefaultValue="-2"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("Partner", "activeTradePartnerId"), ("IsPaired", "A"))
    branch(g, "BrPaired", 0, 0)
    g.link(("IsPaired", "ReturnValue"), ("BrPaired", "Condition"))

    pid = flip(g, "PartnerId", ("Partner", "activeTradePartnerId"), 500, 400)
    g.node("FindPartner", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="DockById",bSelfContext=True)'],
           250, 0, [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                    ("Id", "in", INT, None), ("Dock", "out", OBJ(WORKDOCK), None)])
    g.link(("BrPaired", "then"), ("FindPartner", "execute"))
    g.link(pid, ("FindPartner", "Id"))
    is_valid(g, "PartnerValid", WORKDOCK, 500, -150)
    g.link(("FindPartner", "Dock"), ("PartnerValid", "Object"))
    branch(g, "BrPartnerFound", 550, 0)
    g.link(("FindPartner", "then"), ("BrPartnerFound", "execute"))
    g.link(("PartnerValid", "ReturnValue"), ("BrPartnerFound", "Condition"))
    set_partner(g, "ClearPartner", 800, 0, literal="-1")
    g.link(("BrPartnerFound", "then"), ("ClearPartner", "execute"))
    g.link(("FindPartner", "Dock"), ("ClearPartner", "self"))

    set_partner(g, "ClearSelf", 1100, 100, literal="-1")
    g.link(("GetDock", "Dock"), ("ClearSelf", "self"))
    for src in (("ClearPartner", "then"), ("BrPartnerFound", "else"), ("BrPaired", "else")):
        g.link(src, ("ClearSelf", "execute"))
    return g.render()


def pair_at_cursor():
    g = Graph()
    F = "PairAtCursor"
    get_self(g, "GetPending", "PendingDock", OBJ(WORKDOCK), 0, 400)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 500)
    get_local(g, "GetTarget", F, "Target", OBJ(WORKDOCK), 0, 600)

    g.node("Find", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="FindDockUnderCursor",bSelfContext=True)'],
           0, 0, [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                  ("Dock", "out", OBJ(WORKDOCK), None), ("HitLoc", "out", STRUCT(VECTOR), None)])
    set_local(g, "SetTarget", F, "Target", OBJ(WORKDOCK), 250, 0)
    g.link(("Find", "then"), ("SetTarget", "execute"))
    g.link(("Find", "Dock"), ("SetTarget", "Target"))
    set_local(g, "SetHitLoc", F, "HitLoc", STRUCT(VECTOR), 500, 0)
    g.link(("SetTarget", "then"), ("SetHitLoc", "execute"))
    g.link(("Find", "HitLoc"), ("SetHitLoc", "HitLoc"))

    def clear_pending(name, x, y, after):
        g.node(name, K2 + "K2Node_VariableSet", [self_var("PendingDock")], x, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                ("PendingDock", "in", OBJ(WORKDOCK), None), ("Output_Get", "out", OBJ(WORKDOCK), None)])
        g.link(after, (name, "execute"))

    # no dock under the cursor
    is_valid(g, "TargetValid", WORKDOCK, 750, 200)
    g.link(("GetTarget", "Target"), ("TargetValid", "Object"))
    branch(g, "BrTarget", 750, 0)
    g.link(("SetHitLoc", "then"), ("BrTarget", "execute"))
    g.link(("TargetValid", "ReturnValue"), ("BrTarget", "Condition"))
    # ... with a dock waiting to pair: unpair it if it's paired, else cancel; with none waiting: ask for a dock
    is_valid(g, "PendingValid0", WORKDOCK, 1000, 650)
    g.link(("GetPending", "PendingDock"), ("PendingValid0", "Object"))
    branch(g, "BrWaiting", 1000, 300)
    g.link(("BrTarget", "else"), ("BrWaiting", "execute"))
    g.link(("PendingValid0", "ReturnValue"), ("BrWaiting", "Condition"))
    toast(g, "PopNoDock", 1250, 450, literal="Select a dock first")
    g.link(("BrWaiting", "else"), ("PopNoDock", "execute"))
    get_member(g, "PendingPartner", WORKDOCK, "activeTradePartnerId", INT, 1250, 750)
    g.link(("GetPending", "PendingDock"), ("PendingPartner", "self"))
    branch(g, "BrWasPaired", 1250, 300)
    g.link(("BrWaiting", "then"), ("BrWasPaired", "execute"))
    g.link(int_op(g, "WasPaired", "LessEqual_IntInt", ("PendingPartner", "activeTradePartnerId"), None, 1500, 750, b_default="-2"),
           ("BrWasPaired", "Condition"))
    g.node("UnpairWaiting", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="Unpair",bSelfContext=True)'], 1500, 300,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Dock", "in", OBJ(WORKDOCK), None)])
    g.link(("BrWasPaired", "then"), ("UnpairWaiting", "execute"))
    g.link(("GetPending", "PendingDock"), ("UnpairWaiting", "Dock"))
    s_un = fmt_to_string(g, "FmtUnpaired", "Unpaired dock {a}", [("a", INT)], 1750, 650)
    g.link(dock_id_call(g, "WaitingId", ("GetPending", "PendingDock"), 1500, 900), ("FmtUnpaired", "a"))
    log_msg(g, "LogUnpaired", "GetModAPI", 1750, 300)
    g.link(("UnpairWaiting", "then"), ("LogUnpaired", "execute"))
    g.link((s_un, "ReturnValue"), ("LogUnpaired", "Msg"))
    toast(g, "PopUnpaired", 2000, 300, literal="Unpaired")
    g.link(("LogUnpaired", "then"), ("PopUnpaired", "execute"))
    toast(g, "PopCancelledNoDock", 1500, 450, literal="Pairing cancelled")
    g.link(("BrWasPaired", "else"), ("PopCancelledNoDock", "execute"))
    clear_pending("ClearPendingNoDock", 2250, 300, ("PopUnpaired", "then"))
    g.link(("PopCancelledNoDock", "then"), ("ClearPendingNoDock", "execute"))

    # not a freight dock
    branch(g, "BrFreight", 750, -600)
    g.link(("BrTarget", "then"), ("BrFreight", "execute"))
    g.link(is_freight_call(g, "TargetFreight", ("GetTarget", "Target"), 500, -450), ("BrFreight", "Condition"))
    toast(g, "PopNotFreight", 1000, -750, literal="Only freight docks can be paired")
    g.link(("BrFreight", "else"), ("PopNotFreight", "execute"))
    clear_pending("ClearPendingNotFreight", 1250, -750, ("PopNotFreight", "then"))

    target_id = dock_id_call(g, "TargetId", ("GetTarget", "Target"), 750, 1200)
    pending_id = dock_id_call(g, "PendingId", ("GetPending", "PendingDock"), 1000, 1200)

    # first press: remember the dock
    is_valid(g, "PendingValid", WORKDOCK, 1000, -200)
    g.link(("GetPending", "PendingDock"), ("PendingValid", "Object"))
    branch(g, "BrPending", 1000, 0)
    g.link(("BrFreight", "then"), ("BrPending", "execute"))
    g.link(("PendingValid", "ReturnValue"), ("BrPending", "Condition"))
    g.node("SetPending", K2 + "K2Node_VariableSet", [self_var("PendingDock")], 1250, -350,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("PendingDock", "in", OBJ(WORKDOCK), None), ("Output_Get", "out", OBJ(WORKDOCK), None)])
    g.link(("BrPending", "else"), ("SetPending", "execute"))
    g.link(("GetTarget", "Target"), ("SetPending", "PendingDock"))
    toast(g, "PopSelected", 1500, -350)
    g.link(("SetPending", "then"), ("PopSelected", "execute"))
    # name the key chosen in Mod Options
    get_self(g, "GetPairKey", "PairKey", KEY, 1250, -700)
    g.call("KeyName", "/Script/CoreUObject.Class'/Script/Engine.KismetInputLibrary'", "Key_GetDisplayName", 1500, -700,
           [("Key", "in", KEY, None), ("bLongDisplayName", "in", BOOL, 'DefaultValue="true"'), ("ReturnValue", "out", TEXT, None)])
    g.link(("GetPairKey", "PairKey"), ("KeyName", "Key"))
    g.call("KeyStr", TEXTLIB, "Conv_TextToString", 1750, -700, [("InText", "in", TEXT, None), ("ReturnValue", "out", STR, None)])
    g.link(("KeyName", "ReturnValue"), ("KeyStr", "InText"))
    g.call("SelectedMsg", STRLIB, "Concat_StrStr", 1750, -550,
           [("A", "in", STR, 'DefaultValue="Dock selected - select its partner and press "'), ("B", "in", STR, None),
            ("ReturnValue", "out", STR, None)])
    g.link(("KeyStr", "ReturnValue"), ("SelectedMsg", "B"))
    g.link(("SelectedMsg", "ReturnValue"), ("PopSelected", "Message"))

    # same dock again: cancel
    g.call("SameDock", MATHLIB, "EqualEqual_ObjectObject", 1250, 200,
           [("A", "in", OBJ(WORKDOCK), None), ("B", "in", OBJ(WORKDOCK), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetPending", "PendingDock"), ("SameDock", "A"))
    g.link(("GetTarget", "Target"), ("SameDock", "B"))
    branch(g, "BrSame", 1250, 0)
    g.link(("BrPending", "then"), ("BrSame", "execute"))
    g.link(("SameDock", "ReturnValue"), ("BrSame", "Condition"))
    toast(g, "PopCancelled", 1500, 150, literal="Pairing cancelled")
    g.link(("BrSame", "then"), ("PopCancelled", "execute"))
    clear_pending("ClearPendingCancel", 1750, 150, ("PopCancelled", "then"))

    # different dock: pair them
    def unpair_call(name, dock_src, x, y, after):
        g.node(name, K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="Unpair",bSelfContext=True)'], x, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Dock", "in", OBJ(WORKDOCK), None)])
        g.link(after, (name, "execute"))
        g.link(dock_src, (name, "Dock"))

    unpair_call("UnpairPending", ("GetPending", "PendingDock"), 1500, 0, ("BrSame", "else"))
    unpair_call("UnpairTarget", ("GetTarget", "Target"), 1750, 0, ("UnpairPending", "then"))
    set_partner(g, "PendingToTarget", 2000, 0)
    g.link(("UnpairTarget", "then"), ("PendingToTarget", "execute"))
    g.link(("GetPending", "PendingDock"), ("PendingToTarget", "self"))
    g.link(flip(g, "EncTarget", target_id, 2000, 300), ("PendingToTarget", "activeTradePartnerId"))
    set_partner(g, "TargetToPending", 2250, 0)
    g.link(("PendingToTarget", "then"), ("TargetToPending", "execute"))
    g.link(("GetTarget", "Target"), ("TargetToPending", "self"))
    g.link(flip(g, "EncPending", pending_id, 2250, 300), ("TargetToPending", "activeTradePartnerId"))

    s3 = fmt_to_string(g, "FmtLog", "Paired docks {a} and {b}", [("a", INT), ("b", INT)], 2500, 300)
    g.link(pending_id, ("FmtLog", "a"))
    g.link(target_id, ("FmtLog", "b"))
    toast(g, "PopPaired", 2500, 0)
    g.link(("TargetToPending", "then"), ("PopPaired", "execute"))
    g.link((s3, "ReturnValue"), ("PopPaired", "Message"))
    log_msg(g, "LogPaired", "GetModAPI", 3000, 0)
    g.link(("PopPaired", "then"), ("LogPaired", "execute"))
    g.link((s3, "ReturnValue"), ("LogPaired", "Msg"))
    # plan both directions' water routes
    for i, (name, src) in enumerate((("PlanPending", ("GetPending", "PendingDock")), ("PlanTarget", ("GetTarget", "Target")))):
        user_call(g, name, "PlanRoute", 3250 + 250 * i, 0, ins=[("Dock", OBJ(WORKDOCK))])
        g.link(src, (name, "Dock"))
    g.link(("LogPaired", "then"), ("PlanPending", "execute"))
    g.link(("PlanPending", "then"), ("PlanTarget", "execute"))
    clear_pending("ClearPendingPaired", 3750, 0, ("PlanTarget", "then"))
    return g.render()


def partner_of():
    g = Graph()
    F = "PartnerOf"
    clear_var(g, "ClearResult", [local_var(F, "Result")], "Result", OBJ(WORKDOCK), 0, 0)
    get_local(g, "GetDock", F, "Dock", OBJ(WORKDOCK), 0, 250)
    get_member(g, "Partner", WORKDOCK, "activeTradePartnerId", INT, 250, 250)
    g.link(("GetDock", "Dock"), ("Partner", "self"))
    paired = int_op(g, "IsPaired", "LessEqual_IntInt", ("Partner", "activeTradePartnerId"), None, 500, 250, b_default="-2")
    branch(g, "BrPaired", 250, 0)
    g.link(("ClearResult", "then"), ("BrPaired", "execute"))
    g.link(paired, ("BrPaired", "Condition"))
    pid = flip(g, "PartnerId", ("Partner", "activeTradePartnerId"), 500, 400)
    user_call(g, "FindPartner", "DockById", 500, 0, ins=[("Id", INT)], outs=[("Dock", OBJ(WORKDOCK))])
    g.link(("BrPaired", "then"), ("FindPartner", "execute"))
    g.link(pid, ("FindPartner", "Id"))
    set_local(g, "SetResult", F, "Result", OBJ(WORKDOCK), 750, 0)
    g.link(("FindPartner", "then"), ("SetResult", "execute"))
    g.link(("FindPartner", "Dock"), ("SetResult", "Result"))
    get_local(g, "GetResultForReturn", F, "Result", OBJ(WORKDOCK), 750, -200)
    return g.render()


SPECS = {
    "PairAtCursor": fn_spec(("Find", "execute"), locals_=[("Target", OBJ(WORKDOCK)), ("HitLoc", STRUCT(VECTOR))]),
}


GRAPHS = {
    "Unpair": unpair,
    "PairAtCursor": pair_at_cursor,
    "PartnerOf": partner_of,
}
