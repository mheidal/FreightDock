"""Generic node builders: variable get/set (self, local, member), structs, branches, loops and macros, math,
array / set / map functions, casts, actor lookups and timers. Nothing FreightDock-specific.
"""
from fdgen.core.graph import local_var
from fdgen.core.types import (
    BOOL, CLASSPIN, DOUBLE, EXEC, FLOAT, INT, INT_SET, NAME, NAME_ARRAY, OBJ, STR, STRUCT,
    struct_obj)
from fdgen.core.paths import (
    ACTOR, ACTORCOMP, ARRAYLIB, FOREACH, K2, MACRO_GUIDS, MAPLIB, MAPLOAD_C, MATHLIB, SETLIB, SHIP,
    STATICS, SYSLIB, VECTOR)


def self_var(var):
    return f'VariableReference=(MemberName="{var}",bSelfContext=True)'


def member_of(cls, var):
    return f"VariableReference=(MemberParent=\"/Script/CoreUObject.Class'{cls}'\",MemberName=\"{var}\")"


def get_self(g, name, var, ptype, x, y):
    return g.node(name, K2 + "K2Node_VariableGet", [self_var(var)], x, y, [(var, "out", ptype, None)])


def get_local(g, name, scope, var, ptype, x, y):
    return g.node(name, K2 + "K2Node_VariableGet", [local_var(scope, var)], x, y, [(var, "out", ptype, None)])


def set_local(g, name, scope, var, ptype, x, y):
    return g.node(name, K2 + "K2Node_VariableSet", [local_var(scope, var)], x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   (var, "in", ptype, None), ("Output_Get", "out", ptype, None)])


def get_member(g, name, cls, var, ptype, x, y):
    return g.node(name, K2 + "K2Node_VariableGet", [member_of(cls, var)], x, y,
                  [("self", "in", OBJ(cls), None), (var, "out", ptype, None)])


def set_member(g, name, cls, var, ptype, x, y):
    return g.node(name, K2 + "K2Node_VariableSet", [member_of(cls, var)], x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("self", "in", OBJ(cls), None), (var, "in", ptype, None), ("Output_Get", "out", ptype, None)])


def break_struct(g, name, path, outputs, x, y):
    short = path.split(".")[-1]
    return g.node(name, K2 + "K2Node_BreakStruct", [f"StructType={struct_obj(path)}"], x, y,
                  [(short, "in", STRUCT(path), None)] + [(n, "out", t, None) for n, t in outputs])


def make_struct(g, name, path, inputs, x, y):
    short = path.split(".")[-1]
    return g.node(name, K2 + "K2Node_MakeStruct", [f"StructType={struct_obj(path)}"], x, y,
                  [(n, "in", t, None) for n, t in inputs] + [(short, "out", STRUCT(path), None)])


def set_fields(g, name, path, field, ftype, x, y, more=(), defaults=None):
    """Set Members node exposing `field` (and any extra (field, type) pairs in `more`)."""
    fields = [(field, ftype)] + list(more)
    return g.node(name, K2 + "K2Node_SetFieldsInStruct",
                  [f"StructType={struct_obj(path)}"] +
                  [f'ShowPinForProperties({i})=(PropertyName="{f}",PropertyFriendlyName="{f}",bShowPin=True,bCanToggleVisibility=True)'
                   for i, (f, _) in enumerate(fields)],
                  x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("StructRef", "in", STRUCT(path), None)] +
                  [(f, "in", t, None if f not in (defaults or {}) else f'DefaultValue="{defaults[f]}"')
                   for f, t in fields] +
                  [("StructOut", "out", STRUCT(path), None)])


def branch(g, name, x, y):
    return g.node(name, K2 + "K2Node_IfThenElse", [], x, y,
                  [("execute", "in", EXEC, None), ("Condition", "in", BOOL, None),
                   ("then", "out", EXEC, None), ("else", "out", EXEC, None)])


def is_valid(g, name, cls, x, y):
    return g.call(name, SYSLIB, "IsValid", x, y,
                  [("Object", "in", OBJ(cls), None), ("ReturnValue", "out", BOOL, None)])


def display_name(g, name, cls, x, y):
    return g.call(name, SYSLIB, "GetDisplayName", x, y,
                  [("Object", "in", OBJ(cls), None), ("ReturnValue", "out", STR, None)])


def for_each(g, name, elem_type, x, y):
    arr = elem_type[:1] + elem_type[1:] + ["PinType.ContainerType=Array"]
    return g.node(name, K2 + "K2Node_MacroInstance", [FOREACH], x, y,
                  [("Exec", "in", EXEC, None), ("Array", "in", arr, None),
                   ("LoopBody", "out", EXEC, None), ("Array Element", "out", elem_type, None),
                   ("Array Index", "out", INT, None), ("Completed", "out", EXEC, None)])


def all_ships(g, name, x, y):
    ctype, cdefault = CLASSPIN("/Script/Engine.Actor", SHIP)
    return g.call(name, STATICS, "GetAllActorsOfClass", x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("ActorClass", "in", ctype, cdefault), ("OutActors", "out", OBJ(SHIP, "Array"), None)])


def all_actors(g, name, cls, x, y):
    ctype, cdefault = CLASSPIN(ACTOR, cls)
    return g.call(name, STATICS, "GetAllActorsOfClass", x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("ActorClass", "in", ctype, cdefault), ("OutActors", "out", OBJ(cls, "Array"), None)])


def self_call(g, name, func, x, y, pins):
    return g.node(name, K2 + "K2Node_CallFunction",
                  [f'FunctionReference=(MemberName="{func}",bSelfContext=True)'], x, y, pins)


def comp_owner(g, name, comp_cls, x, y):
    return g.call(name, f"/Script/CoreUObject.Class'{ACTORCOMP}'", "GetOwner", x, y,
                  [("self", "in", OBJ(comp_cls), None), ("ReturnValue", "out", OBJ(ACTOR), None)])


def find_component(g, name, actor_src, comp_cls, x, y):
    ctype, cdefault = CLASSPIN(ACTORCOMP, comp_cls)
    g.call(name, f"/Script/CoreUObject.Class'{ACTOR}'", "GetComponentByClass", x, y,
           [("self", "in", OBJ(ACTOR), None), ("ComponentClass", "in", ctype, cdefault),
            ("ReturnValue", "out", OBJ(comp_cls), None)])
    g.link(actor_src, (name, "self"))
    return (name, "ReturnValue")


def pure_cast(g, name, src, src_cls, to_cls, out_pin, x, y):
    g.node(name, K2 + "K2Node_DynamicCast", [f"TargetType=\"/Script/CoreUObject.Class'{to_cls}'\"", "PureState=Pure"], x, y,
           [("Object", "in", OBJ(src_cls), None), (out_pin, "out", OBJ(to_cls), None), ("bSuccess", "out", BOOL, None)])
    g.link(src, (name, "Object"))
    return (name, out_pin), (name, "bSuccess")


def macro(g, name, macro_name, x, y, pins):
    guid = f",GraphGuid={MACRO_GUIDS[macro_name]}" if macro_name in MACRO_GUIDS else ""
    ref = ("MacroGraphReference=(MacroGraph=\"/Script/Engine.EdGraph'/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:"
           f"{macro_name}'\",GraphBlueprint=\"/Script/Engine.Blueprint'/Engine/EditorBlueprintResources/StandardMacros.StandardMacros'\"{guid})")
    return g.node(name, K2 + "K2Node_MacroInstance", [ref], x, y, pins)


def for_loop(g, name, x, y, first=None, last=None, with_break=False):
    """StandardMacros ForLoop / ForLoopWithBreak. first/last: int literal or None (to link).
    Its exec input is "execute" (ForEachLoop's is "Exec"); links to (name, "Exec") are redirected."""
    g.alias[(name, "Exec")] = (name, "execute")
    pins = [("execute", "in", EXEC, None),
            ("FirstIndex", "in", INT, None if first is None else f'DefaultValue="{first}"'),
            ("LastIndex", "in", INT, None if last is None else f'DefaultValue="{last}"')]
    if with_break:
        pins.append(("Break", "in", EXEC, None))
    pins += [("LoopBody", "out", EXEC, None), ("Index", "out", INT, None), ("Completed", "out", EXEC, None)]
    return macro(g, name, "ForLoopWithBreak" if with_break else "ForLoop", x, y, pins)


def ii(g, name, func, a, b, x, y, b_default=None, out=None):
    """Two-int KismetMathLibrary op (Add/Subtract/Multiply/Divide/Percent/Min/Max/compare)."""
    g.call(name, MATHLIB, func, x, y,
           [("A", "in", INT, None), ("B", "in", INT, None if b_default is None else f'DefaultValue="{b_default}"'),
            ("ReturnValue", "out", out or INT, None)])
    if a:
        g.link(a, (name, "A"))
    if b:
        g.link(b, (name, "B"))
    return (name, "ReturnValue")


def bop(g, name, func, a, b, x, y):
    """BooleanAND / BooleanOR on two sources."""
    g.call(name, MATHLIB, func, x, y, [("A", "in", BOOL, None), ("B", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(a, (name, "A"))
    g.link(b, (name, "B"))
    return (name, "ReturnValue")


def bnot(g, name, a, x, y):
    g.call(name, MATHLIB, "Not_PreBool", x, y, [("A", "in", BOOL, None), ("ReturnValue", "out", BOOL, None)])
    g.link(a, (name, "A"))
    return (name, "ReturnValue")


def arrfn(g, name, func, x, y, pins):
    return g.node(name, K2 + "K2Node_CallArrayFunction",
                  [f'FunctionReference=(MemberParent="{ARRAYLIB}",MemberName="{func}")'], x, y, pins)


def arr_item(g, name, arr_src, idx_src, elem_type, x, y):
    arr_t = elem_type + ["PinType.ContainerType=Array"]
    g.node(name, K2 + "K2Node_GetArrayItem", [], x, y,
           [("Array", "in", arr_t, None), ("Dimension 1", "in", INT, None), ("Output", "out", elem_type, None)])
    g.link(arr_src, (name, "Array"))
    g.link(idx_src, (name, "Dimension 1"))
    return (name, "Output")


def set_contains(g, name, set_src, item_src, x, y):
    g.call(name, SETLIB, "Set_Contains", x, y,
           [("TargetSet", "in", INT_SET, None), ("ItemToFind", "in", INT, None), ("ReturnValue", "out", BOOL, None)])
    g.link(set_src, (name, "TargetSet"))
    g.link(item_src, (name, "ItemToFind"))
    return (name, "ReturnValue")


def set_add(g, name, set_src, item_src, x, y):
    g.call(name, SETLIB, "Set_Add", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetSet", "in", INT_SET, None), ("NewItem", "in", INT, None)])
    g.link(set_src, (name, "TargetSet"))
    g.link(item_src, (name, "NewItem"))
    return name


def set_clear(g, name, set_src, x, y):
    g.call(name, SETLIB, "Set_Clear", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("TargetSet", "in", INT_SET, None)])
    g.link(set_src, (name, "TargetSet"))
    return name


def chain(g, *names):
    for a, b in zip(names, names[1:]):
        g.link((a, "then"), (b, "execute"))


def dmath(g, name, func, a_src, b_src, x, y, a_default=None, b_default=None, pins=("A", "B"), out=DOUBLE):
    """A two-input double KismetMathLibrary call; returns its output."""
    pa, pb = pins
    g.call(name, MATHLIB, func, x, y,
           [(pa, "in", DOUBLE, None if a_default is None else f'DefaultValue="{a_default}"'),
            (pb, "in", DOUBLE, None if b_default is None else f'DefaultValue="{b_default}"'),
            ("ReturnValue", "out", out, None)])
    if a_src:
        g.link(a_src, (name, pa))
    if b_src:
        g.link(b_src, (name, pb))
    return (name, "ReturnValue")


def dmath1(g, name, func, a_src, x, y, pin="A", out=DOUBLE):
    g.call(name, MATHLIB, func, x, y, [(pin, "in", DOUBLE, None), ("ReturnValue", "out", out, None)])
    g.link(a_src, (name, pin))
    return (name, "ReturnValue")


def break_vec(g, name, src, x, y):
    g.call(name, MATHLIB, "BreakVector", x, y,
           [("InVec", "in", STRUCT(VECTOR), None), ("X", "out", DOUBLE, None), ("Y", "out", DOUBLE, None), ("Z", "out", DOUBLE, None)])
    g.link(src, (name, "InVec"))
    return (name, "X"), (name, "Y"), (name, "Z")


def make_vec(g, name, xs, ys, zs, x, y):
    g.call(name, MATHLIB, "MakeVector", x, y,
           [("X", "in", DOUBLE, None), ("Y", "in", DOUBLE, None), ("Z", "in", DOUBLE, None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    for pin, src in (("X", xs), ("Y", ys), ("Z", zs)):
        g.link(src, (name, pin))
    return (name, "ReturnValue")


def user_call(g, name, func, x, y, ins=(), outs=(), impure=True):
    pins = [("execute", "in", EXEC, None), ("then", "out", EXEC, None)] if impure else []
    pins += [(n, "in", t, None) for n, t in ins] + [(n, "out", t, None) for n, t in outs]
    return g.node(name, K2 + "K2Node_CallFunction",
                  [f'FunctionReference=(MemberName="{func}",bSelfContext=True)'], x, y, pins)


def loom_call(g, name, lib, func, x, y, ins=(), outs=()):
    """Call a Loom library function whose first parameter is MapLoad (this BP_MapLoad), with further inputs `ins` and
    outputs `outs` ((pin, type) pairs). Wires a Self node into MapLoad. Returns the call node's name."""
    g.node(name + "_Self", K2 + "K2Node_Self", [], x, y + 200,
           [("self", "out", ['PinType.PinCategory="object"', 'PinType.PinSubCategory="self"'], None)])
    g.call(name, lib, func, x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None), ("MapLoad", "in", OBJ(MAPLOAD_C), None)]
           + [(n, "in", t, None) for n, t in ins] + [(n, "out", t, None) for n, t in outs])
    g.link((name + "_Self", "self"), (name, "MapLoad"))
    return name


def clear_var(g, name, ref_props, var, ptype, x, y):
    """VariableSet with nothing connected: clears an object ref / empties a container."""
    return g.node(name, K2 + "K2Node_VariableSet", ref_props, x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   (var, "in", ptype, None), ("Output_Get", "out", ptype, None)])


def map_find(g, name, map_src, key_src, map_type, value_type, x, y, key_type=NAME):
    g.call(name, MAPLIB, "Map_Find", x, y,
           [("TargetMap", "in", map_type, None), ("Key", "in", key_type, None),
            ("Value", "out", value_type, None), ("ReturnValue", "out", BOOL, None)])
    g.link(map_src, (name, "TargetMap"))
    g.link(key_src, (name, "Key"))


def map_add(g, name, map_src, key_src, value_src, map_type, value_type, x, y, key_type=NAME):
    g.call(name, MAPLIB, "Map_Add", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", map_type, None), ("Key", "in", key_type, None), ("Value", "in", value_type, None)])
    g.link(map_src, (name, "TargetMap"))
    g.link(key_src, (name, "Key"))
    if value_src:
        g.link(value_src, (name, "Value"))


def map_keys(g, name, map_src, map_type, x, y):
    g.call(name, MAPLIB, "Map_Keys", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", map_type, None), ("Keys", "out", NAME_ARRAY, None)])
    g.link(map_src, (name, "TargetMap"))


def int_op(g, name, func, a_src, b_src, x, y, b_default=None):
    g.call(name, MATHLIB, func, x, y,
           [("A", "in", INT, None), ("B", "in", INT, None if b_default is None else f'DefaultValue="{b_default}"'),
            ("ReturnValue", "out", INT if func in ("Add_IntInt", "Subtract_IntInt") else BOOL, None)])
    g.link(a_src, (name, "A"))
    if b_src:
        g.link(b_src, (name, "B"))
    return (name, "ReturnValue")


def actor_loc(g, name, src, x, y):
    g.call(name, f"/Script/CoreUObject.Class'{ACTOR}'", "K2_GetActorLocation", x, y,
           [("self", "in", OBJ(ACTOR), None), ("ReturnValue", "out", STRUCT(VECTOR), None)])
    g.link(src, (name, "self"))
    return (name, "ReturnValue")


def set_self(g, name, var, ptype, x, y, literal=None):
    return g.node(name, K2 + "K2Node_VariableSet", [self_var(var)], x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   (var, "in", ptype, None if literal is None else f'DefaultValue="{literal}"'),
                   ("Output_Get", "out", ptype, None)])


def clear_timer(g, name, func, x, y):
    return g.call(name, SYSLIB, "K2_ClearTimer", x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("Object", "in", OBJ("/Script/CoreUObject.Object"), None),
                   ("FunctionName", "in", STR, f'DefaultValue="{func}"')])


def start_timer(g, name, func, seconds, x, y):
    return g.call(name, SYSLIB, "K2_SetTimer", x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("Object", "in", OBJ("/Script/CoreUObject.Object"), None),
                   ("FunctionName", "in", STR, f'DefaultValue="{func}"'),
                   ("Time", "in", FLOAT, f'DefaultValue="{seconds}"'),
                   ("bLooping", "in", BOOL, 'DefaultValue="true"'),
                   ("ReturnValue", "out", STRUCT("/Script/Engine.TimerHandle"), None)])


def map_contains(g, name, map_src, key_src, map_type, x, y, key_type=INT):
    g.call(name, MAPLIB, "Map_Contains", x, y,
           [("TargetMap", "in", map_type, None), ("Key", "in", key_type, None), ("ReturnValue", "out", BOOL, None)])
    g.link(map_src, (name, "TargetMap"))
    g.link(key_src, (name, "Key"))
    return (name, "ReturnValue")


def map_remove(g, name, map_src, key_src, map_type, x, y, key_type=INT):
    g.call(name, MAPLIB, "Map_Remove", x, y,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("TargetMap", "in", map_type, None), ("Key", "in", key_type, None), ("ReturnValue", "out", BOOL, None)])
    g.link(map_src, (name, "TargetMap"))
    g.link(key_src, (name, "Key"))
    return name


def set_pin_default(g, node, pin, value):
    for i, n in enumerate(g.nodes):
        if n[0] == node:
            pins = [(pn, d, t, f'DefaultValue="{value}"' if pn == pin else dv) for pn, d, t, dv in n[5]]
            g.nodes[i] = n[:5] + (pins,)
            return
    raise KeyError(node)


def inc_self(g, name, var, x, y):
    """var = var + 1 (impure; name is the setter)."""
    get_self(g, name + "Get", var, INT, x, y + 200)
    s = set_self(g, name, var, INT, x, y)
    g.link(ii(g, name + "Plus", "Add_IntInt", (name + "Get", var), None, x + 250, y + 200, b_default="1"), (name, var))
    return s
