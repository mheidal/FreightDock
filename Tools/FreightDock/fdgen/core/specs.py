"""Install specs: fn_spec() describes what WWBlueprintToolset.ImportFunction needs beyond the T3D - signature
(inputs, outputs, locals, purity) and the entry / return wiring, by node label and real pin name.
"""
def pin_type_text(t):
    return "(" + ",".join(part[len("PinType."):] for part in t) + ")"


def fn_spec(entry, inputs=(), outputs=(), locals_=(), returns=(), values=(), pure=False):
    var = lambda items: [{"name": n, "type": pin_type_text(t), "default": d[0] if d else ""} for n, t, *d in items]
    return {"pure": pure, "inputs": var(inputs), "outputs": var(outputs), "locals": var(locals_),
            "entry": list(entry), "returns": [list(r) for r in returns], "returnValues": [list(v) for v in values]}
