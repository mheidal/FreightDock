"""Voyages: what BPL_FDVoyage (Loom) needs from BP_MapLoad - VoyageTick (the voyage timer's function), and
SpawnStandIn and SpawnFling (Loom can't spawn actors).
"""
from fdgen.core.graph import Graph
from fdgen.core.types import CLASSPIN, COLLISION_PIN, EXEC, OBJ, STRUCT
from fdgen.core.paths import ACTOR, FD_FLING_CLASS, K2, TRANSFORM, VOYAGE_LIB
from fdgen.core.specs import fn_spec
from fdgen.core.nodes import get_local, loom_call


def spawn_stand_in():
    """SpawnStandIn(Model, At) -> Proxy: an actor of class Model at At, a ship's stand-in (for
    BPL_FDVoyage.StartVoyage: Loom can't spawn actors)."""
    g = Graph()
    F = "SpawnStandIn"
    ctype, _ = CLASSPIN(ACTOR, ACTOR)
    get_local(g, "GetModel", F, "Model", ctype, 0, 150)
    get_local(g, "GetAt", F, "At", STRUCT(TRANSFORM), 0, 250)
    g.node("Spawn", K2 + "K2Node_SpawnActorFromClass", [], 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Class", "in", ctype, None), ("ReturnValue", "out", OBJ(ACTOR), None),
            ("SpawnTransform", "in", STRUCT(TRANSFORM), None),
            ("CollisionHandlingOverride", "in", COLLISION_PIN, 'DefaultValue="AlwaysSpawn"'),
            ("Owner", "in", OBJ(ACTOR), None)])
    g.link(("GetModel", "Model"), ("Spawn", "Class"))
    g.link(("GetAt", "At"), ("Spawn", "SpawnTransform"))
    return g.render()


def voyage_tick():
    """VoyageTick (the voyage timer, every BPL_FDVoyage.TickStep of game time): BPL_FDVoyage.VoyageTick - moves every stand-in,
    waits at the target, turns for home and hands arrivals to VoyageArrive (see there)."""
    g = Graph()
    loom_call(g, "Call", VOYAGE_LIB, "VoyageTick", 0, 0)
    return g.render()


def spawn_fling():
    """SpawnFling(At) -> Fling: a BP_FDFling at At (for BPL_FDVoyage.VoyageArrive: Loom can't spawn actors)."""
    g = Graph()
    get_local(g, "GetAt", "SpawnFling", "At", STRUCT(TRANSFORM), 0, 250)
    fct, fcd = CLASSPIN(ACTOR, FD_FLING_CLASS)
    g.node("Spawn", K2 + "K2Node_SpawnActorFromClass", [], 250, 0,
           [("execute", "in", EXEC, None), ("then", "out", EXEC, None),
            ("Class", "in", fct, fcd), ("ReturnValue", "out", OBJ(FD_FLING_CLASS), None),
            ("SpawnTransform", "in", STRUCT(TRANSFORM), None),
            ("CollisionHandlingOverride", "in", COLLISION_PIN, 'DefaultValue="AlwaysSpawn"'),
            ("Owner", "in", OBJ(ACTOR), None)])
    g.link(("GetAt", "At"), ("Spawn", "SpawnTransform"))
    return g.render()


SPECS = {
    "VoyageTick": fn_spec(("Call", "execute")),
    "SpawnStandIn": fn_spec(("Spawn", "execute"), inputs=[("Model", CLASSPIN(ACTOR, ACTOR)[0]), ("At", STRUCT(TRANSFORM))],
                            outputs=[("Proxy", OBJ(ACTOR))],
                            returns=[("Spawn", "then")], values=[("Spawn", "ReturnValue", "Proxy")]),
    "SpawnFling": fn_spec(("Spawn", "execute"), inputs=[("At", STRUCT(TRANSFORM))], outputs=[("Fling", OBJ(FD_FLING_CLASS))],
                          returns=[("Spawn", "then")], values=[("Spawn", "ReturnValue", "Fling")]),
}


GRAPHS = {
    "SpawnStandIn": spawn_stand_in,
    "VoyageTick": voyage_tick,
    "SpawnFling": spawn_fling,
}
