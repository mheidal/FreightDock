"""Pairing: TargetOf, whose logic is in Loom (BPL_FDNet); this graph only calls it, keeping the name and pins its
callers use. Docks join freight networks in the Freight Dock panel (stored in activeTradePartnerId, see
BPL_FDNet.lm); the pairing key (PairAtCursor, Unpair) is gone.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import OBJ
from fdgen.core.paths import NET_LIB, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import get_local, loom_call


def target_of():
    """TargetOf(Dock) -> Target: BPL_FDNet.TargetOf."""
    g = Graph()
    get_local(g, "GetDock", "TargetOf", "Dock", OBJ(WORKDOCK), 0, 250)
    loom_call(g, "Call", NET_LIB, "TargetOf", 250, 0, ins=[("Dock", OBJ(WORKDOCK))],
              outs=[("ReturnValue", OBJ(WORKDOCK))])
    g.link(("GetDock", "Dock"), ("Call", "Dock"))
    return g.render()


SPECS = {
    "TargetOf": fn_spec(("Call", "execute"), inputs=[("Dock", OBJ(WORKDOCK))], outputs=[("Target", OBJ(WORKDOCK))],
                         returns=[("Call", "then")], values=[("Call", "ReturnValue", "Target")]),
}


GRAPHS = {
    "TargetOf": target_of,
}
