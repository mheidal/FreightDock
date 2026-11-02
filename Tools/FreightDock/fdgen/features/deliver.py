""""Deliver now" button: injected under the food list of the dock's Load Resources panel (ShipPreparationWidget),
polled each tick, and DeliverSelected backdates the loading clock so the ship departs.
"""
from fdgen.core.graph import Graph, local_var
from fdgen.core.types import BOOL, CLASSPIN, DOUBLE, EXEC, INT, KEY, MAP_INT_ACTOR, MAP_INT_DOUBLE, OBJ, STRUCT
from fdgen.core.paths import (
    DELIVER_BUTTON_CLASS, K2, MAPLIB, MATHLIB, MODAPI, PANEL, PC, SHIPPREP, STATICS,
    UBUTTON, USERWIDGET, UWIDGET, VBOX, VBOXSLOT, VECTOR, WLIB, WORKDOCK)
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import (
    arrfn, bop, branch, clear_var, for_each, for_loop, get_local, get_member, get_self,
    int_op, is_valid, map_add, map_find, pure_cast, set_local, set_pin_default, set_self, user_call)
from fdgen.core.text import fmt_to_string, log_msg, toast
from fdgen.features.docks import dock_id_call, is_freight_call


def inject_deliver_buttons():
    """InjectDeliverButtons: when the selected dock (FindDockUnderCursor - its window is the one open) is a paired
    freight dock, every ship preparation panel (ShipPreparationWidget, the "Load resources onto ship" part of a dock's
    window; closed windows' panels linger, hidden, until collected) gets a WBP_FDDeliverButton below its food section
    (appended to the nearest Vertical Box above its arcolist_food) unless its last child already is one. Each button goes into
    DeliverBtns.
    Locals: W (User Widget), Box (Vertical Box), Made (User Widget), Cur (Widget)."""
    g = Graph()
    F = "InjectDeliverButtons"
    get_local(g, "GetW", F, "W", OBJ(USERWIDGET), 0, 400)
    get_local(g, "GetBox", F, "Box", OBJ(VBOX), 0, 600)
    get_local(g, "GetMade", F, "Made", OBJ(USERWIDGET), 0, 700)
    get_self(g, "GetBtns", "DeliverBtns", OBJ(UBUTTON, "Array"), 0, 750)

    # the selected dock must be a paired freight dock
    g.node("FindSel", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="FindDockUnderCursor",bSelfContext=True)'], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Dock", "out", OBJ(WORKDOCK), None), ("HitLoc", "out", STRUCT(VECTOR), None)])
    is_valid(g, "DockOk", WORKDOCK, 250, 300)
    g.link(("FindSel", "Dock"), ("DockOk", "Object"))
    get_member(g, "PartnerEnc", WORKDOCK, "activeTradePartnerId", INT, 250, 450)
    g.link(("FindSel", "Dock"), ("PartnerEnc", "self"))
    paired = int_op(g, "Paired", "LessEqual_IntInt", ("PartnerEnc", "activeTradePartnerId"), None, 500, 450, b_default="-2")
    ok = bop(g, "Ok0", "BooleanAND", ("DockOk", "ReturnValue"), paired, 750, 350)
    ok = bop(g, "Ok", "BooleanAND", ok, is_freight_call(g, "Freight", ("FindSel", "Dock"), 500, 600), 1000, 350)
    branch(g, "BrOk", 250, 0)
    g.link(("FindSel", "then"), ("BrOk", "execute"))
    g.link(ok, ("BrOk", "Condition"))

    ctype, cdefault = CLASSPIN(USERWIDGET, SHIPPREP)
    g.call("Panels", WLIB, "GetAllWidgetsOfClass", 500, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("FoundWidgets", "out", OBJ(USERWIDGET, "Array"), None),
            ("WidgetClass", "in", ctype, cdefault), ("TopLevelOnly", "in", BOOL, 'DefaultValue="false"')])
    g.link(("BrOk", "then"), ("Panels", "execute"))
    for_each(g, "ForPanels", OBJ(USERWIDGET), 1000, 0)
    g.link(("Panels", "then"), ("ForPanels", "Exec"))
    g.link(("Panels", "FoundWidgets"), ("ForPanels", "Array"))
    set_local(g, "SetW", F, "W", OBJ(USERWIDGET), 1250, 0)
    g.link(("ForPanels", "LoopBody"), ("SetW", "execute"))
    g.link(("ForPanels", "Array Element"), ("SetW", "W"))

    # the food section: the nearest Vertical Box above the panel's food list (arcolist_food)
    prep, _ = pure_cast(g, "AsPrep", ("GetW", "W"), USERWIDGET, SHIPPREP, "AsShip Preparation Widget", 1250, 850)
    get_member(g, "FoodList", SHIPPREP, "arcolist_food", OBJ(VBOX), 1500, 850)
    g.link(prep, ("FoodList", "self"))
    set_local(g, "StartUp", F, "Cur", OBJ(UWIDGET), 1400, 0)
    g.link(("SetW", "then"), ("StartUp", "execute"))
    g.link(("FoodList", "arcolist_food"), ("StartUp", "Cur"))
    clear_var(g, "ClearBox", [local_var(F, "Box")], "Box", OBJ(VBOX), 1450, 0)
    g.link(("StartUp", "then"), ("ClearBox", "execute"))
    for_loop(g, "Up", 1500, 0, first=1, last=6, with_break=True)
    g.link(("ClearBox", "then"), ("Up", "Exec"))
    get_local(g, "GetCur", F, "Cur", OBJ(UWIDGET), 1500, 1000)
    g.call("Parent", f"/Script/CoreUObject.Class'{UWIDGET}'", "GetParent", 1750, 1000,
           [("self", "in", OBJ(UWIDGET), None), ("ReturnValue", "out", OBJ(PANEL), None)])
    g.link(("GetCur", "Cur"), ("Parent", "self"))
    set_local(g, "StepUp", F, "Cur", OBJ(UWIDGET), 1750, 150)
    g.link(("Up", "LoopBody"), ("StepUp", "execute"))
    g.link(("Parent", "ReturnValue"), ("StepUp", "Cur"))
    box, is_box = pure_cast(g, "AsBox", ("GetCur", "Cur"), UWIDGET, VBOX, "AsVertical Box", 2000, 1000)
    branch(g, "BrIsBox", 2000, 150)
    g.link(("StepUp", "then"), ("BrIsBox", "execute"))
    g.link(is_box, ("BrIsBox", "Condition"))
    set_local(g, "SetBox", F, "Box", OBJ(VBOX), 2250, 150)
    g.link(("BrIsBox", "then"), ("SetBox", "execute"))
    g.link(box, ("SetBox", "Box"))
    g.link(("SetBox", "then"), ("Up", "Break"))
    is_valid(g, "BoxOk", VBOX, 1750, 300)
    g.link(("GetBox", "Box"), ("BoxOk", "Object"))

    branch(g, "BrBox", 1750, 0)
    g.link(("Up", "Completed"), ("BrBox", "execute"))
    g.link(("BoxOk", "ReturnValue"), ("BrBox", "Condition"))

    # already there? (its last child is our button)
    P = f"/Script/CoreUObject.Class'{PANEL}'"
    g.call("NKids", P, "GetChildrenCount", 2000, 1000, [("self", "in", OBJ(PANEL), None), ("ReturnValue", "out", INT, None)])
    g.link(("GetBox", "Box"), ("NKids", "self"))
    last_i = int_op(g, "LastIdx", "Subtract_IntInt", ("NKids", "ReturnValue"), None, 2250, 1000, b_default="1")
    g.call("LastKid", P, "GetChildAt", 2500, 1000,
           [("self", "in", OBJ(PANEL), None), ("Index", "in", INT, None), ("ReturnValue", "out", OBJ(UWIDGET), None)])
    g.link(("GetBox", "Box"), ("LastKid", "self"))
    g.link(last_i, ("LastKid", "Index"))
    last_btn, has_btn = pure_cast(g, "LastAsOurs", ("LastKid", "ReturnValue"), UWIDGET, DELIVER_BUTTON_CLASS,
                                  "AsWBP FDDeliver Button", 2750, 1000)
    get_member(g, "OldBtn", DELIVER_BUTTON_CLASS, "DeliverButton", OBJ(UBUTTON), 3000, 1000)
    g.link(last_btn, ("OldBtn", "self"))
    branch(g, "BrHas", 2000, 0)
    g.link(("BrBox", "then"), ("BrHas", "execute"))
    g.link(has_btn, ("BrHas", "Condition"))
    arrfn(g, "KeepBtn", "Array_AddUnique", 2250, -150,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", OBJ(UBUTTON, "Array"), None),
           ("NewItem", "in", OBJ(UBUTTON), None), ("ReturnValue", "out", INT, None)])
    g.link(("BrHas", "then"), ("KeepBtn", "execute"))
    g.link(("GetBtns", "DeliverBtns"), ("KeepBtn", "TargetArray"))
    g.link(("OldBtn", "DeliverButton"), ("KeepBtn", "NewItem"))

    # add one
    g.call("PCForWidget", STATICS, "GetPlayerController", 2250, 600,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ(PC), None)])
    wct, wcd = CLASSPIN(USERWIDGET, DELIVER_BUTTON_CLASS)
    g.node("Make", "/Script/UMGEditor.K2Node_CreateWidget", [], 2250, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("Class", "in", wct, wcd),
            ("OwningPlayer", "in", OBJ(PC), None), ("ReturnValue", "out", OBJ(USERWIDGET), None)])
    g.link(("BrHas", "else"), ("Make", "execute"))
    g.link(("PCForWidget", "ReturnValue"), ("Make", "OwningPlayer"))
    set_local(g, "SetMade", F, "Made", OBJ(USERWIDGET), 2500, 150)
    g.link(("Make", "then"), ("SetMade", "execute"))
    g.link(("Make", "ReturnValue"), ("SetMade", "Made"))
    g.call("AddBtn", f"/Script/CoreUObject.Class'{VBOX}'", "AddChildToVerticalBox", 2750, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(VBOX), None),
            ("Content", "in", OBJ(UWIDGET), None), ("ReturnValue", "out", OBJ(VBOXSLOT), None)])
    g.link(("SetMade", "then"), ("AddBtn", "execute"))
    g.link(("GetBox", "Box"), ("AddBtn", "self"))
    g.link(("GetMade", "Made"), ("AddBtn", "Content"))
    VS = f"/Script/CoreUObject.Class'{VBOXSLOT}'"
    g.call("Centre", VS, "SetHorizontalAlignment", 3000, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(VBOXSLOT), None),
            ("InHorizontalAlignment", "in", ['PinType.PinCategory="byte"',
             "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/SlateCore.EHorizontalAlignment'\""], 'DefaultValue="HAlign_Center"')])
    g.link(("AddBtn", "then"), ("Centre", "execute"))
    g.link(("AddBtn", "ReturnValue"), ("Centre", "self"))
    g.call("Gap", VS, "SetPadding", 3250, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(VBOXSLOT), None),
            ("InPadding", "in", STRUCT("/Script/SlateCore.Margin"), 'DefaultValue="(Left=0.000000,Top=10.000000,Right=0.000000,Bottom=4.000000)"')])
    g.link(("Centre", "then"), ("Gap", "execute"))
    g.link(("AddBtn", "ReturnValue"), ("Gap", "self"))
    made_ours, _ = pure_cast(g, "MadeAsOurs", ("GetMade", "Made"), USERWIDGET, DELIVER_BUTTON_CLASS, "AsWBP FDDeliver Button", 3250, 600)
    get_member(g, "NewBtn", DELIVER_BUTTON_CLASS, "DeliverButton", OBJ(UBUTTON), 3500, 600)
    g.link(made_ours, ("NewBtn", "self"))
    arrfn(g, "AddToBtns", "Array_AddUnique", 3500, 150,
          [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetArray", "in", OBJ(UBUTTON, "Array"), None),
           ("NewItem", "in", OBJ(UBUTTON), None), ("ReturnValue", "out", INT, None)])
    g.link(("Gap", "then"), ("AddToBtns", "execute"))
    g.link(("GetBtns", "DeliverBtns"), ("AddToBtns", "TargetArray"))
    g.link(("NewBtn", "DeliverButton"), ("AddToBtns", "NewItem"))
    return g.render()


def deliver_tick():
    """DeliverTick (from PairKeyTick, also while paused): for 30 frames after a left click, InjectDeliverButtons (a
    dock window may have just opened); and when any of DeliverBtns has just been pressed, DeliverSelected.
    Local: AnyDown."""
    g = Graph()
    F = "DeliverTick"
    get_self(g, "GetFrames", "InjectFrames", INT, 0, 400)
    get_self(g, "GetBtns", "DeliverBtns", OBJ(UBUTTON, "Array"), 0, 500)
    get_self(g, "GetWas", "DeliverBtnWasPressed", BOOL, 0, 600)
    get_local(g, "GetAny", F, "AnyDown", BOOL, 0, 650)
    g.call("PC", STATICS, "GetPlayerController", 0, 700,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ(PC), None)])
    g.call("Clicked", f"/Script/CoreUObject.Class'{PC}'", "WasInputKeyJustPressed", 250, 700,
           [("self", "in", OBJ(PC), None), ("Key", "in", KEY, 'DefaultValue="LeftMouseButton"'), ("ReturnValue", "out", BOOL, None)])
    g.link(("PC", "ReturnValue"), ("Clicked", "self"))
    branch(g, "BrClicked", 0, 0)
    g.link(("Clicked", "ReturnValue"), ("BrClicked", "Condition"))
    set_self(g, "Arm", "InjectFrames", INT, 250, -150, literal="30")
    g.link(("BrClicked", "then"), ("Arm", "execute"))
    armed = int_op(g, "Armed", "Greater_IntInt", ("GetFrames", "InjectFrames"), None, 500, 400, b_default="0")
    branch(g, "BrArmed", 500, 0)
    g.link(("Arm", "then"), ("BrArmed", "execute"))
    g.link(("BrClicked", "else"), ("BrArmed", "execute"))
    g.link(armed, ("BrArmed", "Condition"))
    set_self(g, "CountDown", "InjectFrames", INT, 750, -150)
    g.link(("BrArmed", "then"), ("CountDown", "execute"))
    g.link(int_op(g, "Less1", "Subtract_IntInt", ("GetFrames", "InjectFrames"), None, 750, 400, b_default="1"),
           ("CountDown", "InjectFrames"))
    user_call(g, "Inject", "InjectDeliverButtons", 1000, -150)
    g.link(("CountDown", "then"), ("Inject", "execute"))

    # any button down?
    g.node("ClearAny", K2 + "K2Node_VariableSet", [local_var(F, "AnyDown")], 1250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("AnyDown", "in", BOOL, 'DefaultValue="false"'), ("Output_Get", "out", BOOL, None)])
    for src in (("Inject", "then"), ("BrArmed", "else")):
        g.link(src, ("ClearAny", "execute"))
    for_each(g, "ForBtns", OBJ(UBUTTON), 1500, 0)
    g.link(("ClearAny", "then"), ("ForBtns", "Exec"))
    g.link(("GetBtns", "DeliverBtns"), ("ForBtns", "Array"))
    is_valid(g, "BtnOk", UBUTTON, 1500, 400)
    g.link(("ForBtns", "Array Element"), ("BtnOk", "Object"))
    branch(g, "BrBtnOk", 1750, 150)
    g.link(("ForBtns", "LoopBody"), ("BrBtnOk", "execute"))
    g.link(("BtnOk", "ReturnValue"), ("BrBtnOk", "Condition"))
    g.call("Down", f"/Script/CoreUObject.Class'{UBUTTON}'", "IsPressed", 1750, 550,
           [("self", "in", OBJ(UBUTTON), None), ("ReturnValue", "out", BOOL, None)])
    g.link(("ForBtns", "Array Element"), ("Down", "self"))
    g.node("SetAny", K2 + "K2Node_VariableSet", [local_var(F, "AnyDown")], 2000, 150,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("AnyDown", "in", BOOL, None), ("Output_Get", "out", BOOL, None)])
    g.link(("BrBtnOk", "then"), ("SetAny", "execute"))
    g.link(bop(g, "AnyOr", "BooleanOR", ("GetAny", "AnyDown"), ("Down", "ReturnValue"), 2000, 400), ("SetAny", "AnyDown"))

    g.call("NotWas", MATHLIB, "Not_PreBool", 1750, 700, [("A", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetWas", "DeliverBtnWasPressed"), ("NotWas", "A"))
    edge = bop(g, "Edge", "BooleanAND", ("GetAny", "AnyDown"), ("NotWas", "ReturnValue"), 2000, 700)
    branch(g, "BrEdge", 1750, -150)
    g.link(("ForBtns", "Completed"), ("BrEdge", "execute"))
    g.link(edge, ("BrEdge", "Condition"))
    user_call(g, "Deliver", "DeliverSelected", 2000, -300)
    g.link(("BrEdge", "then"), ("Deliver", "execute"))
    set_self(g, "Remember", "DeliverBtnWasPressed", BOOL, 2250, -150)
    g.link(("Deliver", "then"), ("Remember", "execute"))
    g.link(("BrEdge", "else"), ("Remember", "execute"))
    g.link(("GetAny", "AnyDown"), ("Remember", "DeliverBtnWasPressed"))
    return g.render()


def deliver_selected():
    """DeliverSelected (the Deliver now button): the selected freight dock's ship sails now with what it has - its
    loading clock (LoadingSince) is set far back so FreightTick's max-wait check passes. Ship away (in Voyages) or
    nothing loaded yet: a toast."""
    g = Graph()
    F = "DeliverSelected"
    get_self(g, "GetSince", "LoadingSince", MAP_INT_DOUBLE, 0, 400)
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 500)
    g.node("FindSel", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="FindDockUnderCursor",bSelfContext=True)'], 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Dock", "out", OBJ(WORKDOCK), None), ("HitLoc", "out", STRUCT(VECTOR), None)])
    is_valid(g, "SelOk", WORKDOCK, 250, 300)
    g.link(("FindSel", "Dock"), ("SelOk", "Object"))
    branch(g, "BrSel", 250, 0)
    g.link(("FindSel", "then"), ("BrSel", "execute"))
    g.link(("SelOk", "ReturnValue"), ("BrSel", "Condition"))
    did = dock_id_call(g, "SelId", ("FindSel", "Dock"), 250, 450)
    get_self(g, "GetVoyages", "Voyages", MAP_INT_ACTOR, 0, 600)
    g.call("Away", MAPLIB, "Map_Contains", 500, 600,
           [("TargetMap", "in", MAP_INT_ACTOR, None), ("Key", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("GetVoyages", "Voyages"), ("Away", "TargetMap"))
    g.link(did, ("Away", "Key"))
    branch(g, "BrAway", 400, 0)
    g.link(("BrSel", "then"), ("BrAway", "execute"))
    g.link(("Away", "ReturnValue"), ("BrAway", "Condition"))
    toast(g, "UnderWay", 500, -250, literal="The ship is under way")
    g.link(("BrAway", "then"), ("UnderWay", "execute"))
    map_find(g, "Clock", ("GetSince", "LoadingSince"), did, MAP_INT_DOUBLE, DOUBLE, 500, 400, key_type=INT)
    branch(g, "BrLoading", 500, 0)
    g.link(("BrAway", "else"), ("BrLoading", "execute"))
    g.link(("Clock", "ReturnValue"), ("BrLoading", "Condition"))
    map_add(g, "Backdate", ("GetSince", "LoadingSince"), did, None, MAP_INT_DOUBLE, DOUBLE, 750, -100, key_type=INT)
    set_pin_default(g, "Backdate", "Value", "-1000000000000000.0")
    g.link(("BrLoading", "then"), ("Backdate", "execute"))
    s = fmt_to_string(g, "FmtDeliver", "Deliver now: dock {d}", [("d", INT)], 750, 300)
    g.link(did, ("FmtDeliver", "d"))
    log_msg(g, "Log", "GetModAPI", 1000, -100)
    g.link(("Backdate", "then"), ("Log", "execute"))
    g.link((s, "ReturnValue"), ("Log", "Msg"))
    toast(g, "Nothing", 750, 150, literal="Nothing loaded yet")
    g.link(("BrLoading", "else"), ("Nothing", "execute"))
    return g.render()


SPECS = {
    "InjectDeliverButtons": fn_spec(("FindSel", "execute"), locals_=[("W", OBJ(USERWIDGET)), ("Box", OBJ(VBOX)), ("Made", OBJ(USERWIDGET)),
                                                                    ("Cur", OBJ(UWIDGET))]),
    "DeliverTick": fn_spec(("BrClicked", "execute"), locals_=[("AnyDown", BOOL, "false")]),
    "DeliverSelected": fn_spec(("FindSel", "execute")),
}


GRAPHS = {
    "InjectDeliverButtons": inject_deliver_buttons,
    "DeliverTick": deliver_tick,
    "DeliverSelected": deliver_selected,
}
