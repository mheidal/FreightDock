"""Pin types: lists of PinType.* fragments for Graph.node pins (EXEC, INT, OBJ(path), STRUCT(path), maps, arrays).
"""
from fdgen.core.paths import ACTOR, AGENTMOD, FOOTCELL, GRIDACTOR, ISM, SHIP, VECTOR, WORKERSLOT


def struct_obj(path):
    return f"\"/Script/CoreUObject.ScriptStruct'{path}'\""


# Pin type helpers -> list of PinType.* fragments
def T(cat, sub=None, subobj=None, container=None, value=None):
    parts = [f'PinType.PinCategory="{cat}"']
    if sub:
        parts.append(f'PinType.PinSubCategory="{sub}"')
    if subobj:
        parts.append(f"PinType.PinSubCategoryObject={struct_obj(subobj)}")
    if container:
        parts.append(f"PinType.ContainerType={container}")
    if value:
        vcat, vobj = value
        v = f'TerminalCategory="{vcat}"'
        if vobj:
            v += f",TerminalSubCategoryObject={struct_obj(vobj)}"
        parts.append(f"PinType.PinValueType=({v})")
    return parts


EXEC = T("exec")


NAME = T("name")


STR = T("string")


TEXT = T("text")


BOOL = T("bool")


INT = T("int")


DOUBLE = T("real", sub="double")


def STRUCT(path): return T("struct", subobj=path)


def OBJ(path, container=None):
    parts = ['PinType.PinCategory="object"', f"PinType.PinSubCategoryObject=\"/Script/CoreUObject.Class'{path}'\""]
    if container:
        parts.append(f"PinType.ContainerType={container}")
    return parts


def CLASSPIN(base, default):
    return (['PinType.PinCategory="class"', f"PinType.PinSubCategoryObject=\"/Script/CoreUObject.Class'{base}'\""],
            f"DefaultObject=\"/Script/CoreUObject.Class'{default}'\"")


def MAP_NAME_TO(path): return T("name", container="Map", value=("struct", path))


def MAP_NAME_TO_INT(): return T("name", container="Map", value=("int", None))


NAME_ARRAY = T("name", container="Array")


INT_SET = T("int", container="Set")


INT_ARRAY = T("int", container="Array")


KEY = STRUCT("/Script/InputCore.Key")


MOD_MAP = T("name", container="Map", value=("struct", AGENTMOD))


SLOT_ARRAY = STRUCT(WORKERSLOT) + ["PinType.ContainerType=Array"]


INTVECTOR_T = STRUCT("/Script/CoreUObject.IntVector")


FOOT_MAP = T("struct", subobj="/Script/CoreUObject.IntVector", container="Map", value=("struct", FOOTCELL))


ISM_ARRAY = OBJ(ISM, "Array")


GRIDACTOR_ARRAY = OBJ(GRIDACTOR, "Array")


VEC_ARRAY = T("struct", subobj=VECTOR, container="Array")


MAP_NAME_INT = MAP_NAME_TO_INT()


MAP_INT_DOUBLE = ['PinType.PinCategory="int"', "PinType.ContainerType=Map",
                  'PinType.PinValueType=(TerminalCategory="real",TerminalSubCategory="double")']


FLOAT = T("real", sub="float")


SEARCHCASE_PIN = ['PinType.PinCategory="byte"',
                  "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/CoreUObject.ESearchCase'\""]


SPLINE_SPACE = ['PinType.PinCategory="byte"', "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/Engine.ESplineCoordinateSpace'\""]


COLLISION_PIN = ['PinType.PinCategory="byte"',
                 "PinType.PinSubCategoryObject=\"/Script/CoreUObject.Enum'/Script/Engine.ESpawnActorCollisionHandlingMethod'\""]


INT_ARRAY_T = T("int", container="Array")


def MAP_INT_OBJ(cls):
    return ['PinType.PinCategory="int"', "PinType.ContainerType=Map",
            f"PinType.PinValueType=(TerminalCategory=\"object\",TerminalSubCategoryObject=\"/Script/CoreUObject.Class'{cls}'\")"]


MAP_INT_ACTOR = MAP_INT_OBJ(ACTOR)


MAP_INT_SHIP = MAP_INT_OBJ(SHIP)


MAP_INT_VECTOR = ['PinType.PinCategory="int"', "PinType.ContainerType=Map",
                  f"PinType.PinValueType=(TerminalCategory=\"struct\",TerminalSubCategoryObject={struct_obj(VECTOR)})"]


MAP_INT_INT = ['PinType.PinCategory="int"', "PinType.ContainerType=Map", 'PinType.PinValueType=(TerminalCategory="int")']


MAP_INT_BOOL = ['PinType.PinCategory="int"', "PinType.ContainerType=Map", 'PinType.PinValueType=(TerminalCategory="bool")']


STR_SET = T("string", container="Set")


STR_ARRAY = T("string", container="Array")
