"""PlanRoute: BPL_FDVoyage.RequestRoute - queues one dock's route to its target; BPL_FDVoyage plans it a little each
frame (RouteStep), an A* over route cells.
"""
from fdgen.core.graph import Graph
from fdgen.core.types import OBJ
from fdgen.core.paths import VOYAGE_LIB, WORKDOCK
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import get_local, loom_call


def plan_route():
    """PlanRoute(Dock): BPL_FDVoyage.RequestRoute - queue Dock's route to its target (planned over the next frames)."""
    g = Graph()
    get_local(g, "GetDock", "PlanRoute", "Dock", OBJ(WORKDOCK), 0, 250)
    loom_call(g, "Call", VOYAGE_LIB, "RequestRoute", 250, 0, ins=[("Dock", OBJ(WORKDOCK))])
    g.link(("GetDock", "Dock"), ("Call", "Dock"))
    return g.render()


SPECS = {
    "PlanRoute": fn_spec(("Call", "execute"), inputs=[("Dock", OBJ(WORKDOCK))]),
}


GRAPHS = {
    "PlanRoute": plan_route,
}
