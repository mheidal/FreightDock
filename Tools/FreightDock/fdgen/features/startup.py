"""BP_Startup: RegisterFreightDock adds the freight dock building (a copy of the trade dock's GridActor rows), its
icon, its own unlock (a copy of the trade dock's, without prerequisites) and its strings.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import BOOL, EXEC, NAME, OBJ, STR, T
from fdgen.core.paths import FREIGHT_DOCK_CLASS, K2, MODAPI, STRLIB
from fdgen.core.nodes import get_self
from fdgen.core.specs import fn_spec
from fdgen.core.text import LOG_PREFIX


# GridActors (ModAPI name of GridactorDefs_Sync) columns; copied from the trade dock unless overridden
GRIDACTOR_COLUMNS = ["Description", "GridActor", "Icon", "Quality", "SupportedImprovements", "TooltipTags", "Variants",
                     "asHouseTier", "asIndustryDef", "catalyst", "constructionTime", "cost1", "cost2", "cost3", "cost4",
                     "ct1", "ct2", "ct3", "ct4", "customBuildCue", "decorType", "detailCue", "guildSpecialty", "hardLabor",
                     "industrialLabor", "isDraggableWall", "limitOne", "maxAgents_contextual", "maxHealth",
                     "minMaintenanceInterval", "norefund", "randomlyRotate", "refundRule", "requiresConstruction",
                     "stringKey", "structureType", "supportedIndustryRecipes", "toolbarGroup", "toolbarGroupSort",
                     "unlockPrerequisite", "useCustomIcon", "workerColor"]


FREIGHT_ROW = "freightDock"


# unlocks columns; copied from the trade dock's unlock unless overridden
UNLOCK_COLUMNS = ["useGridActorForLoc", "Title", "Description", "demoLocked", "IsHidden", "subCategory",
                  "giftableInDemo", "giftable", "giftPool", "researchable", "scienceCost", "researchTier",
                  "unlockedByDefault", "childUnlocks", "associatedGridActor", "prerequisiteUnlocks", "tierSortOrder",
                  "associatedRecipe", "isQuestRelated", "showMailEvenAsChildUnlock", "secretPrerequisite"]


TRADE_UNLOCK = "unlock.navaltradeDock"


FREIGHT_UNLOCK = "unlock.freightDock"


# researchable on its own in the trade dock's tier, sorted just after it (30; the storage dock is 40)
UNLOCK_OVERRIDES = {
    "associatedGridActor": FREIGHT_ROW,
    "prerequisiteUnlocks": "()",
    "tierSortOrder": "35",
}


FREIGHT_LOC = "freightdock.building.freightDock"


FREIGHT_OVERRIDES = {
    "GridActor": f"/Script/Engine.BlueprintGeneratedClass'{FREIGHT_DOCK_CLASS}'",
    "stringKey": FREIGHT_LOC,
    "Description": FREIGHT_LOC + ".desc",
    "toolbarGroupSort": "36",
    "unlockPrerequisite": FREIGHT_UNLOCK,
}


FREIGHT_STRINGS = {
    FREIGHT_LOC: "Freight Dock",
    FREIGHT_LOC + ".desc": "Crew a ship that carries goods your paired freight dock's island needs, then returns",
}


def register_freight_dock():
    """BP_Startup: add the freight dock building (a copy of the trade dock's rows), its icon, its unlock and its
    strings."""
    g = Graph()
    MAPI = f"/Script/CoreUObject.Class'{MODAPI}'"
    get_self(g, "GetModAPI", "ModAPI", OBJ(MODAPI), 0, 400)
    prev = None
    x = 0

    def chain(n):
        nonlocal prev
        if prev:
            g.link((prev, "then"), (n, "execute"))
        g.link(("GetModAPI", "ModAPI"), (n, "self"))
        prev = n

    def add_row(name, table, row):
        nonlocal x
        chain(g.call(name, MAPI, "AddDataTableRow", x, 0,
                     [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
                      ("datatableName", "in", NAME, f'DefaultValue="{table}"'), ("rowId", "in", NAME, f'DefaultValue="{row}"'),
                      ("ReturnValue", "out", BOOL, None)]))
        x += 250

    def read(name, table, row, col):
        nonlocal x
        chain(g.call(name, MAPI, "ReadDataTableValue", x, 0,
                     [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
                      ("datatableName", "in", NAME, f'DefaultValue="{table}"'), ("rowId", "in", NAME, f'DefaultValue="{row}"'),
                      ("ColumnName", "in", NAME, f'DefaultValue="{col}"'), ("ReturnValue", "out", STR, None)]))
        x += 250

    def write(name, table, row, col, value_src=None, literal=None):
        nonlocal x
        chain(g.call(name, MAPI, "WriteDataTableValue", x, 0,
                     [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
                      ("datatableName", "in", NAME, f'DefaultValue="{table}"'), ("rowId", "in", NAME, f'DefaultValue="{row}"'),
                      ("ColumnName", "in", NAME, f'DefaultValue="{col}"'),
                      ("valueStringified", "in", STR, None if literal is None else f'DefaultValue="{literal}"'),
                      ("ReturnValue", "out", BOOL, None)]))
        if value_src:
            g.link(value_src, (name, "valueStringified"))
        x += 250

    def copy(prefix, table, col, src="navaltradeDock", dst=FREIGHT_ROW, overrides=None):
        if overrides is None:
            overrides = FREIGHT_OVERRIDES if table == "GridActors" else {}
        if col in overrides:
            write(f"{prefix}Set_{col}", table, dst, col, literal=overrides[col].replace('"', '\\"'))
        else:
            read(f"{prefix}Get_{col}", table, src, col)
            write(f"{prefix}Set_{col}", table, dst, col, value_src=(f"{prefix}Get_{col}", "ReturnValue"))

    read("CheckTrade", "GridActors", "navaltradeDock", "GridActor")
    add_row("AddDefRow", "GridActors", FREIGHT_ROW)
    for col in GRIDACTOR_COLUMNS:
        copy("Def", "GridActors", col)
    add_row("AddIconRow", "BuildingIcons", FREIGHT_ROW)
    copy("Icon", "BuildingIcons", "Icon")
    add_row("AddUnlockRow", "unlocks", FREIGHT_UNLOCK)
    for col in UNLOCK_COLUMNS:
        copy("Unlock", "unlocks", col, src=TRADE_UNLOCK, dst=FREIGHT_UNLOCK, overrides=UNLOCK_OVERRIDES)

    # strings: "dev" first, then "en" (ModAPI requirement)
    mapt = T("name", container="Map", value=("string", None))
    pins = []
    for i, (k, v) in enumerate(FREIGHT_STRINGS.items()):
        pins += [(f"Key {i}", "in", NAME, f'DefaultValue="{k}"'), (f"Value {i}", "in", STR, f'DefaultValue="{v}"')]
    g.node("Strings", K2 + "K2Node_MakeMap", [f"NumInputs={len(FREIGHT_STRINGS)}"], x, 400,
           pins + [("Map", "out", mapt, None)])
    for lang in ("dev", "en"):
        n = g.call(f"Strings_{lang}", MAPI, "AddNewStrings", x, 0,
                   [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
                    ("langId", "in", NAME, f'DefaultValue="{lang}"'), ("idStringPairs", "in", mapt, None),
                    ("ReturnValue", "out", BOOL, None)])
        chain(n)
        g.link(("Strings", "Map"), (n, "idStringPairs"))
        x += 250

    # log what the new row ended up with
    read("CheckActor", "GridActors", FREIGHT_ROW, "GridActor")
    read("CheckIcon", "BuildingIcons", FREIGHT_ROW, "Icon")
    read("CheckUnlock", "unlocks", FREIGHT_UNLOCK, "associatedGridActor")
    read("CheckTier", "unlocks", FREIGHT_UNLOCK, "researchTier")
    g.call("UnlockStr", STRLIB, "Conv_BoolToString", x - 250, 850,
           [("InBool", "in", BOOL, None), ("ReturnValue", "out", STR, None)])
    g.link(("AddUnlockRow", "ReturnValue"), ("UnlockStr", "InBool"))
    g.call("RowStr", STRLIB, "Conv_BoolToString", x - 250, 700,
           [("InBool", "in", BOOL, None), ("ReturnValue", "out", STR, None)])
    g.link(("AddDefRow", "ReturnValue"), ("RowStr", "InBool"))
    parts = [(LOG_PREFIX + "Freight dock registered: trade GridActor=", None), ("", ("CheckTrade", "ReturnValue")),
             (", added row ", None), ("", ("RowStr", "ReturnValue")),
             (", GridActor=", None), ("", ("CheckActor", "ReturnValue")),
             (", Icon=", None), ("", ("CheckIcon", "ReturnValue")),
             (", added unlock ", None), ("", ("UnlockStr", "ReturnValue")),
             (", unlock building=", None), ("", ("CheckUnlock", "ReturnValue")),
             (", tier=", None), ("", ("CheckTier", "ReturnValue"))]
    s = None
    for i, (lit, src) in enumerate(parts):
        n = g.call(f"Cat{i}", STRLIB, "Concat_StrStr", x + 250 * i, 700,
                   [("A", "in", STR, None), ("B", "in", STR, None if src else f'DefaultValue="{lit}"'),
                    ("ReturnValue", "out", STR, None)])
        if s:
            g.link((s, "ReturnValue"), (n, "A"))
        if src:
            g.link(src, (n, "B"))
        s = n
    # BP_Startup has no Stamp(): let ModAPI prepend the date
    g.call("LogDone", MAPI, "LogMessage", x + 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("self", "in", OBJ(MODAPI), None),
            ("Msg", "in", STR, None), ("doPrependDate", "in", BOOL, 'DefaultValue="true"')])
    chain("LogDone")
    g.link((s, "ReturnValue"), ("LogDone", "Msg"))
    return g.render()


SPECS = {
    "RegisterFreightDock": fn_spec(("CheckTrade", "execute")),
}


GRAPHS = {
    "RegisterFreightDock": register_freight_dock,
}
