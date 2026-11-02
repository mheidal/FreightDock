"""Mod Options: the pairing key and the depart-partially-loaded timeout (RegisterOptions, in BP_Startup), and
reading them back each tick (ReadPairKey, PairKeyTick - also the per-tick hook chain for other features).
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, DOUBLE, EXEC, INT, KEY, OBJ, STR, T
from fdgen.core.paths import K2, MODAPI, STATICS
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import branch, get_self, map_find, set_pin_default, set_self, user_call


PAIR_KEY_OPTION = "freightdock.pairKey"


PAIR_KEY_DEFAULT = "F5"


DEPART_OPTION = "freightdock.departAfter"


# option value -> MaxWaitSeconds (game seconds from the first freight aboard; "Never" = effectively never)
DEPART_CHOICES = {"120 s": "120.0", "180 s": "180.0", "240 s": "240.0", "Never": "1000000000.0"}


DEPART_DEFAULT = "120 s"


# option value -> key name (the main-row 0, not the numpad one)
PAIR_KEYS = {**{f"F{i}": f"F{i}" for i in range(1, 11)}, "0": "Zero"}


def register_options():
    """BP_Startup: the mod's entries in Settings -> Mod Options (the pairing key; how long a partly loaded ship waits)."""
    g = Graph()
    MAPI = f"/Script/CoreUObject.Class'{MODAPI}'"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 400)
    g.node("Keys", K2 + "K2Node_MakeArray", [f"NumInputs={len(PAIR_KEYS)}"], 0, 550,
           [(f"[{i}]", "in", STR, f'DefaultValue="{v}"') for i, v in enumerate(PAIR_KEYS)]
           + [("Array", "out", T("string", container="Array"), None)])
    g.call("PairKey", MAPI, "RegisterModOptions", 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
            ("optionId", "in", STR, f'DefaultValue="{PAIR_KEY_OPTION}"'),
            ("optionDisplayName", "in", STR, 'DefaultValue="Freight Dock: pairing key"'),
            ("Values", "in", T("string", container="Array"), None),
            ("DefaultValue", "in", STR, f'DefaultValue="{PAIR_KEY_DEFAULT}"'),
            ("optionDescription", "in", STR, 'DefaultValue="Pairs the selected freight dock with the next one you select."'),
            ("ReturnValue", "out", BOOL, None)])
    g.link(("GetModAPI", "ModAPI"), ("PairKey", "self"))
    g.link(("Keys", "Array"), ("PairKey", "Values"))
    g.node("Waits", K2 + "K2Node_MakeArray", [f"NumInputs={len(DEPART_CHOICES)}"], 250, 550,
           [(f"[{i}]", "in", STR, f'DefaultValue="{v}"') for i, v in enumerate(DEPART_CHOICES)]
           + [("Array", "out", T("string", container="Array"), None)])
    g.call("DepartAfter", MAPI, "RegisterModOptions", 500, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
            ("optionId", "in", STR, f'DefaultValue="{DEPART_OPTION}"'),
            ("optionDisplayName", "in", STR, 'DefaultValue="Freight Dock: depart partly loaded after"'),
            ("Values", "in", T("string", container="Array"), None),
            ("DefaultValue", "in", STR, f'DefaultValue="{DEPART_DEFAULT}"'),
            ("optionDescription", "in", STR, 'DefaultValue="How long a freight ship waits, from its first cargo loaded, before it sails with what it has. Never: it waits until full or nothing more is wanted."'),
            ("ReturnValue", "out", BOOL, None)])
    g.link(("PairKey", "then"), ("DepartAfter", "execute"))
    g.link(("GetModAPI", "ModAPI"), ("DepartAfter", "self"))
    g.link(("Waits", "Array"), ("DepartAfter", "Values"))
    return g.render()


def read_pair_key():
    """ReadPairKey (BeginPlay, and whenever a mod option changes): PairKey = the key chosen in Mod Options;
    MaxWaitSeconds = the chosen partial-load wait."""
    g = Graph()
    MAPI = f"/Script/CoreUObject.Class'{MODAPI}'"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 400)
    g.call("Read", MAPI, "ReadModOptionValue", 0, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None), ("optionId", "in", STR, f'DefaultValue="{PAIR_KEY_OPTION}"'),
            ("fallbackValue", "in", STR, f'DefaultValue="{PAIR_KEY_DEFAULT}"'), ("ReturnValue", "out", STR, None)])
    g.link(("GetModAPI", "ModAPI"), ("Read", "self"))
    mapt = T("string", container="Map", value=("struct", "/Script/InputCore.Key"))
    pins = []
    for i, (opt, key) in enumerate(PAIR_KEYS.items()):
        pins += [(f"Key {i}", "in", STR, f'DefaultValue="{opt}"'), (f"Value {i}", "in", KEY, f'DefaultValue="{key}"')]
    g.node("Keys", K2 + "K2Node_MakeMap", [f"NumInputs={len(PAIR_KEYS)}"], 250, 450, pins + [("Map", "out", mapt, None)])
    map_find(g, "Find", ("Keys", "Map"), ("Read", "ReturnValue"), mapt, KEY, 500, 300, key_type=STR)
    branch(g, "BrKnown", 250, 0)
    g.link(("Read", "then"), ("BrKnown", "execute"))
    g.link(("Find", "ReturnValue"), ("BrKnown", "Condition"))
    set_self(g, "SetKey", "PairKey", KEY, 500, -150)
    g.link(("BrKnown", "then"), ("SetKey", "execute"))
    g.link(("Find", "Value"), ("SetKey", "PairKey"))
    set_self(g, "SetDefault", "PairKey", KEY, 500, 150)
    set_pin_default(g, "SetDefault", "PairKey", PAIR_KEYS[PAIR_KEY_DEFAULT])
    g.link(("BrKnown", "else"), ("SetDefault", "execute"))

    g.call("ReadWait", MAPI, "ReadModOptionValue", 750, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None), ("optionId", "in", STR, f'DefaultValue="{DEPART_OPTION}"'),
            ("fallbackValue", "in", STR, f'DefaultValue="{DEPART_DEFAULT}"'), ("ReturnValue", "out", STR, None)])
    g.link(("GetModAPI", "ModAPI"), ("ReadWait", "self"))
    g.link(("SetKey", "then"), ("ReadWait", "execute"))
    g.link(("SetDefault", "then"), ("ReadWait", "execute"))
    wmap = T("string", container="Map") + ['PinType.PinValueType=(TerminalCategory="real",TerminalSubCategory="double")']
    wpins = []
    for i, (opt, secs) in enumerate(DEPART_CHOICES.items()):
        wpins += [(f"Key {i}", "in", STR, f'DefaultValue="{opt}"'), (f"Value {i}", "in", DOUBLE, f'DefaultValue="{secs}"')]
    g.node("Waits", K2 + "K2Node_MakeMap", [f"NumInputs={len(DEPART_CHOICES)}"], 1000, 450, wpins + [("Map", "out", wmap, None)])
    map_find(g, "FindWait", ("Waits", "Map"), ("ReadWait", "ReturnValue"), wmap, DOUBLE, 1250, 300, key_type=STR)
    branch(g, "BrWaitKnown", 1000, 0)
    g.link(("ReadWait", "then"), ("BrWaitKnown", "execute"))
    g.link(("FindWait", "ReturnValue"), ("BrWaitKnown", "Condition"))
    set_self(g, "SetWait", "MaxWaitSeconds", DOUBLE, 1250, -150)
    g.link(("BrWaitKnown", "then"), ("SetWait", "execute"))
    g.link(("FindWait", "Value"), ("SetWait", "MaxWaitSeconds"))
    set_self(g, "SetWaitDefault", "MaxWaitSeconds", DOUBLE, 1250, 150, literal=DEPART_CHOICES[DEPART_DEFAULT])
    g.link(("BrWaitKnown", "else"), ("SetWaitDefault", "execute"))
    return g.render()


def pair_key_tick():
    """PairKeyTick (Event Tick, also while paused): PairAtCursor when PairKey was just pressed; then StandInClick,
    DebugCells and DeliverTick."""
    g = Graph()
    get_self(g, "GetKey", "PairKey", KEY, 0, 400)
    g.call("PC", STATICS, "GetPlayerController", 0, 250,
           [("PlayerIndex", "in", INT, 'DefaultValue="0"'), ("ReturnValue", "out", OBJ("/Script/Engine.PlayerController"), None)])
    g.call("Pressed", "/Script/CoreUObject.Class'/Script/Engine.PlayerController'", "WasInputKeyJustPressed", 250, 300,
           [("self", "in", OBJ("/Script/Engine.PlayerController"), None), ("Key", "in", KEY, None), ("ReturnValue", "out", BOOL, None)])
    g.link(("PC", "ReturnValue"), ("Pressed", "self"))
    g.link(("GetKey", "PairKey"), ("Pressed", "Key"))
    branch(g, "BrPressed", 0, 0)
    g.link(("Pressed", "ReturnValue"), ("BrPressed", "Condition"))
    user_call(g, "Pair", "PairAtCursor", 250, 0)
    g.link(("BrPressed", "then"), ("Pair", "execute"))
    user_call(g, "Click", "StandInClick", 500, 0)
    g.link(("Pair", "then"), ("Click", "execute"))
    g.link(("BrPressed", "else"), ("Click", "execute"))
    user_call(g, "Cells", "DebugCells", 750, 0)
    g.link(("Click", "then"), ("Cells", "execute"))
    user_call(g, "Deliver", "DeliverTick", 1000, 0)
    g.link(("Cells", "then"), ("Deliver", "execute"))
    return g.render()


SPECS = {
    "RegisterOptions": fn_spec(("PairKey", "execute")),
    "ReadPairKey": fn_spec(("Read", "execute")),
    "PairKeyTick": fn_spec(("BrPressed", "execute")),
}


GRAPHS = {
    "RegisterOptions": register_options,
    "ReadPairKey": read_pair_key,
    "PairKeyTick": pair_key_tick,
}
