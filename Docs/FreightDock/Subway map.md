# FreightDock: subway-style network map (future release)

A stylised map of the colony's freight networks in the manner of a transit diagram. Idea from 2026-11-09; analysed and
decided 2026-11-11. Not part of 2.0.

## What maps onto what

| Transit map | FreightDock |
|---|---|
| Station | Dock |
| Line | Network (its fixed colour and number) |
| Interchange | A dock on two or three networks |
| Train | A ship under way |

A line reads as "any two stations on it are connected". That matches a network: every provider on it can serve every
requester on it, even though ships sail direct.

## Decided

- **A line is a network:** one line through all of the network's docks, joined by the shortest total length (a
  spanning tree). It shows membership, not provider-requester pairs and not the routes sailed.
- **Scope:** every network in the colony, each one switchable on and off.
- **Layout:** docks stay at their true positions, snapped to a coarse grid; links are straight runs with 45-degree
  bends. No free rearranging of stations: automatic schematic layout is a hard problem, and the map would stop
  matching the world.

## Open

- A toggle on the existing map (`WBP_FDMapPanel`), or a new panel over a large part of the screen. Showing the whole
  colony with every station name favours the large panel: the existing map only has the space above the dock window.
- Where the per-network switches go. The network GUI's rows could carry them.
- How a station shows its roles. The map's red (providing) and blue (requesting) could become a half-and-half ring.

## What exists to build on

- `WBP_FDMapPanel`: zoom, pan, fit, the render target, markers redrawn twice a second, network colours, hover labels.
- Drawing is by canvas lines, boxes, triangles and regular polygons. There are no rounded joins: a bend is covered
  with a filled circle.
- Text drawn into the render target does not show, so station names are widgets. Today only the hovered dock has one.

## Parts, by difficulty

1. **Flat terrain:** one water colour, one land colour, optionally coarsened into blocky islands. A recolour of the
   terrain pass.
2. **Station markers:** a white circle with a dark ring; a capsule across the bands for an interchange.
3. **Lines:** a spanning tree per network over all of its docks, drawn with 45-degree bends.
4. **Parallel bands** where two networks share a link: each line offset sideways by its width, corners fixed. Most
   visual bugs will be here.
5. **All station names:** a pool of text widgets, placed by trying eight positions and taking the first free one,
   hidden below a zoom level. Overlap in dense areas is the risk.
6. **Islands as clean 45-degree outlines** instead of blocks. Cosmetic over part 1.
7. **Shared trunks:** lines of different networks running together between islands even when they share no dock
   pair. Needs a common skeleton to route all lines along.

## Stages

1. Parts 1 to 5. One or two test rounds; the risk is visual polish, not game logic.
2. Ships as dots moving along their line, lines with an active job drawn bolder, a legend.
3. Parts 6 and 7, only if stage 1 looks too sparse.

## Known weak points

- A network's line can change shape when a dock joins it, because the shortest tree changes.
- Lines cross land. That is normal for the style but differs from the route view.
- Two docks side by side need nudging apart so their markers don't overlap.
