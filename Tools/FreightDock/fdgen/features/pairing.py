"""Pairing: PartnerOf, Unpair and PairAtCursor (the pairing key). Their logic is in Loom (BPL_FDNet, BPL_FDPairing);
these graphs only call it, keeping the names and pins their callers use. Pairs are stored as freight networks in
activeTradePartnerId (see BPL_FDNet.lm).
"""
from fdgen.core.graph import Graph
from fdgen.core.types import OBJ
from fdgen.core.paths import NET_LIB, PAIRING_LIB, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import get_local, loom_call


def unpair():
    """Unpair(Dock): BPL_FDNet.Unpair - the dock leaves its networks, and their other members leave them too."""
    g = Graph()
    get_local(g, "GetDock", "Unpair", "Dock", OBJ(WORKDOCK), 0, 250)
    loom_call(g, "Call", NET_LIB, "Unpair", 250, 0, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(("GetDock", "Dock"), ("Call", "Dock"))
    return g.render()


def pair_at_cursor():
    """PairAtCursor: BPL_FDPairing.PairAtCursor (select, pair, cancel, unpair)."""
    g = Graph()
    loom_call(g, "Call", PAIRING_LIB, "PairAtCursor", 0, 0)
    return g.render()


def partner_of():
    """PartnerOf(Dock) -> Partner: BPL_FDNet.PartnerOf."""
    g = Graph()
    get_local(g, "GetDock", "PartnerOf", "Dock", OBJ(WORKDOCK), 0, 250)
    loom_call(g, "Call", NET_LIB, "PartnerOf", 250, 0, ins=[("Dock", OBJ(WORKDOCK))],
              outs=[("ReturnValue", OBJ(WORKDOCK))])
    g.link(("GetDock", "Dock"), ("Call", "Dock"))
    return g.render()


SPECS = {
    "Unpair": fn_spec(("Call", "execute"), inputs=[("Dock", OBJ(WORKDOCK))]),
    "PairAtCursor": fn_spec(("Call", "execute")),
    "PartnerOf": fn_spec(("Call", "execute"), inputs=[("Dock", OBJ(WORKDOCK))], outputs=[("Partner", OBJ(WORKDOCK))],
                         returns=[("Call", "then")], values=[("Call", "ReturnValue", "Partner")]),
}


GRAPHS = {
    "Unpair": unpair,
    "PairAtCursor": pair_at_cursor,
    "PartnerOf": partner_of,
}
