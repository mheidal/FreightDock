"""Deliver now: DeliverSelected, called by the Freight Dock panel's button (WBP_FDPanel), calls Loom
(BPL_FDLoad.DeliverSelected): the selected dock's ship sails now with what it has.
"""
from fdgen.core.graph import Graph
from fdgen.core.paths import LOAD_LIB
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import loom_call


def deliver_selected():
    """DeliverSelected: BPL_FDLoad.DeliverSelected."""
    g = Graph()
    loom_call(g, "Call", LOAD_LIB, "DeliverSelected", 0, 0)
    return g.render()


SPECS = {
    "DeliverSelected": fn_spec(("Call", "execute")),
}


GRAPHS = {
    "DeliverSelected": deliver_selected,
}
