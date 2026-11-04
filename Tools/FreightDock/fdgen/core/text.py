"""Text and logging nodes: Format Text, string conversion and concatenation, LogMessage (prefixed with Stamp()),
and Toast.
"""
from fdgen.core.types import BOOL, EXEC, INT, OBJ, STR, TEXT
from fdgen.core.paths import K2, MODAPI, STRLIB, TEXTLIB


# Starts every FreightDock log line (after the date), so the mod's lines stand out in a shared modlog.
LOG_PREFIX = "[FreightDock] "


def log_msg(g, name, modapi_get, x, y, literal=None):
    """LogMessage node, prefixed with Stamp() ("[yyyy-mm-dd hh:mm:ss] "); target wired from an existing Get ModAPI node.
    Links to (name, "Msg") go to the message part."""
    n = g.call(name, f"/Script/CoreUObject.Class'{MODAPI}'", "LogMessage", x, y,
               [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                ("self", "in", OBJ(MODAPI), None), ("Msg", "in", STR, None),
                ("doPrependDate", "in", BOOL, 'DefaultValue="false"')])
    g.link((modapi_get, "ModAPI"), (n, "self"))
    g.node(name + "_Stamp", K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="Stamp",bSelfContext=True)'],
           x - 250, y + 200, [("Result", "out", STR, None)])
    g.call(name + "_Cat", STRLIB, "Concat_StrStr", x, y + 200,
           [("A", "in", STR, None), ("B", "in", STR, None if literal is None else f'DefaultValue="{literal}"'),
            ("ReturnValue", "out", STR, None)])
    g.link((name + "_Stamp", "Result"), (name + "_Cat", "A"))
    g.link((name + "_Cat", "ReturnValue"), (n, "Msg"))
    g.alias[(n, "Msg")] = (name + "_Cat", "B")
    return n


def int_text(g, name, x, y, digits=1):
    """Conv_IntToText without grouping, at least `digits` digits. Input pin "Value"."""
    return g.call(name, TEXTLIB, "Conv_IntToText", x, y,
                  [("Value", "in", INT, None), ("bAlwaysSign", "in", BOOL, 'DefaultValue="false"'),
                   ("bUseGrouping", "in", BOOL, 'DefaultValue="false"'),
                   ("MinimumIntegralDigits", "in", INT, f'DefaultValue="{digits}"'), ("ReturnValue", "out", TEXT, None)])


def fmt_to_string(g, name, pattern, args, x, y):
    """Format Text + Conv_TextToString. args: [(argName, type)]. Returns the ToString node name.
    Integer args go through int_text (no thousands separators); links to (name, arg) reach its input."""
    g.node(name, K2 + "K2Node_FormatText", [f'PinNames({i})="{a}"' for i, (a, _) in enumerate(args)], x, y,
           [("Format", "in", TEXT, f'DefaultTextValue=INVTEXT("{pattern}")'), ("Result", "out", TEXT, None)]
           + [(a, "in", TEXT if t == INT else t, None) for a, t in args])
    for i, (a, t) in enumerate(args):
        if t == INT:
            conv = int_text(g, f"{name}_{a}Txt", x - 250, y + 120 * (i + 1))
            g.link((conv, "ReturnValue"), (name, a))
            g.alias[(name, a)] = (conv, "Value")
    s = g.call(name + "_Str", TEXTLIB, "Conv_TextToString", x + 250, y,
               [("InText", "in", TEXT, None), ("ReturnValue", "out", STR, None)])
    g.link((name, "Result"), (s, "InText"))
    return s


def toast(g, name, x, y, literal=None):
    """Call BP_MapLoad's Toast(Message): on-screen message via WBP_FDToast."""
    return g.node(name, K2 + "K2Node_CallFunction", ['FunctionReference=(MemberName="Toast",bSelfContext=True)'], x, y,
                  [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
                   ("Message", "in", STR, None if literal is None else f'DefaultValue="{literal}"')])


def concat_parts(g, prefix, parts, x, y):
    """Concat_StrStr chain over parts: each a literal string or a (node, pin) string source. Returns the last node."""
    last = None
    for i, part in enumerate(parts):
        lit = part if isinstance(part, str) else None
        n = g.call(f"{prefix}{i}", STRLIB, "Concat_StrStr", x + 250 * i, y,
                   [("A", "in", STR, None), ("B", "in", STR, None if lit is None else f'DefaultValue="{lit}"'),
                    ("ReturnValue", "out", STR, None)])
        if last:
            g.link((last, "ReturnValue"), (n, "A"))
        if lit is None:
            g.link(part, (n, "B"))
        last = n
    return last


def to_str(g, name, func, in_pin, in_type, src, x, y, lib=None):
    g.call(name, lib or STRLIB, func, x, y, [(in_pin, "in", in_type, None), ("ReturnValue", "out", STR, None)])
    g.link(src, (name, in_pin))
    return (name, "ReturnValue")
