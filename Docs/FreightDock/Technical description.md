# FreightDock: technical description

FreightDock is a Whiskerwood mod that moves goods between islands in bulk. Freight Docks join numbered networks as
providers, requesters or both. A dispatcher gives each idle provider a job: a set of goods to load from its input
warehouses and deliver to one requester on a shared network. The provider's ship then:
1. loads the job's manifest;
2. sails to the requester along a planned water route;
3. delivers into the requester dock's cargo, for the requester's workers to unload into its output warehouses;
4. sails home.

The player-facing description is the top-level `README.md`. This file covers how the mod works. Design reasoning and
history are in [Design decisions.md](Design%20decisions.md) and [Many-to-many links.md](Many-to-many%20links.md).

**Status:** version 2.1 (`Content/Mods/FreightDock/FreightDock.uplugin`, UE 5.8), for Whiskerwood 0.7.211. Version 1.x paired docks one to
one; a 1.x colony is converted on load (see Migration).

## Assets

All the mod's assets are in `Content/Mods/FreightDock`:

| Asset | Role |
|---|---|
| `BP_Startup` | Runs at the first main-menu load: registers the building, its unlock and the Stevedore modifier (`Loom/BPL_FDSetup`) |
| `BP_MainMenuLoad` | Loom. Runs at every main-menu load: registers the Mod Options in the player's language, and again when the language changes |
| `BP_MapLoad` | Holds all state of a loaded colony and the generated graphs; calls the Loom libraries |
| `navaldock_freight` | The Freight Dock building: a child of `navaldock_trade`, with the trade dock's look |
| `WBP_FDToast` | On-screen messages (copy, paste and undo of memberships) |
| `Loom/BPL_FDStore` | Colony-wide data in the colony's event flags: names, jobs, demand ages, the version |
| `Loom/BPL_FDNet` | Base library: membership encoding, network queries, the building index, dock names, stock and deficits, job state |
| `Loom/BPL_FDDispatch` | The dispatcher: demand, supply, scoring, jobs, idle reasons |
| `Loom/BPL_FDLoad` | `FreightTick`: the loading plan, departure, restoring jobs after a load |
| `Loom/BPL_FDVoyage` | Route cells, route search, courses, voyages, buildings added to the route map |
| `Loom/BPL_FDPairing` | The per-frame tick, network arcs, hover highlights, the route line |
| `Loom/BPL_FDOptions`, `Loom/BPL_FDText` | The Mod Options; every player-facing string and its lookup |
| `Loom/BP_FDFling` | The unloading animation at the requester |
| `Loom/BPL_FDCheat`, `UI/WBP_FDProf` | Development only; nothing calls them in a release |
| `UI/WBP_FDPanel` | The dock GUI, beside the game's dock window |
| `UI/WBP_FDNetPanel`, `UI/WBP_FDNetRow`, `UI/WBP_FDNetTip` | The network GUI: its table, rows and good tooltips |
| `UI/WBP_FDMapPanel` | The network map |
| `UI/WBP_FDWantRow`, `UI/WBP_FDIncomingRow`, `UI/WBP_FDLinkRow` | Rows of the dock GUI: manifest, INCOMING, clickable links |
| `UI/WBP_FDRename`, `UI/WBP_FDTip`, `UI/WBP_FDMembersTip`, `UI/WBP_FDRoleLine` | The rename popup and the tooltips |
| `Route/SM_RouteStrip`, `Route/M_RouteLine` | The mesh and material of the route line, also used for the debug cell overlay |

- **Loom:** the `.lm` files are [Loom](https://loom.pierrekin.me/) sources. With the Loom editor plugin installed and
  the editor open, saving one rebuilds its Blueprint; that Blueprint must not be edited by hand. Cooking needs only
  the built assets.
- **Generated graphs:** BP_MapLoad's function graphs come from the `fdgen` package in `Tools/FreightDock`, installed
  with `python -m fdgen.install`; see `Tools/FreightDock/README.md`. Most are now thin calls into the Loom
  libraries. Still generated in full: the rescan, the route-map cell functions, spawning actors (Loom can't) and a
  few display functions.
- **Hand-built:** BP_MapLoad's Event Graph, `Toast`, `StockpileToString`, `CollectionToString`, `LogDocks` and
  `WBP_FDToast`.
- **Layering:** Loom refuses Blueprints that use each other. `BPL_FDStore` and `BPL_FDText` are bases; `BPL_FDNet`
  uses them; everything else uses `BPL_FDNet` and never the other way round. Jobs therefore live in BP_MapLoad's
  variables, not in a dispatcher object.

## Registration

- **Building:** a `freightDock` row in `GridActors` and `BuildingIcons`, copied from the trade dock
  (`navaltradeDock`) with the mod's own actor class, name and description.
- **Unlock:** its own research (`unlock.freightDock`), copied from the trade dock's unlock, in the trade dock's tier
  and sorted just after it, with no prerequisite.
- **Stevedore modifier:** `mod.stevedore` in the AgentModifiers table: a copy of `mod.constructionyardWorker` with
  +10 carry capacity and no expiry.
- **Mod Options** (`BPL_FDOptions`):
  - **Depart after** (`freightdock.departAfter`): 120 s, 180 s, 240 s or Never. Default 120 s. Never is stored as
    1e9 seconds.
  - **Minimum load** (`freightdock.minLoad`): None, 25, 50, 75 or 90 %. Default None.
- **Strings:** every player-facing string is in `BPL_FDText.Strings()`, added as English; `T`, `T1`, `T2` look a key
  up in the player's language first.

## Runtime (BP_MapLoad)

### Events

| Event | Calls |
|---|---|
| BeginPlay | Store ModAPI, bind the delegates below, read the options, start the freight timer (`TickSeconds`) |
| `onLoadingFinished` | Index the buildings and docks, then `ScanNow` |
| `onBuildingSpawned` | `OnBuildingChanged`, which now does nothing. `WBP_FDPanel` binds the same delegate in Loom to get the actor (see Rescan) |
| `onOptionChanged` | `ReadPairKey`, which reads both Mod Options (`BPL_FDOptions.ReadOptions`) |
| Freight timer | `FreightTick` (`BPL_FDLoad.FreightTick`), then `SyncStevedores` |
| Event Tick (also while paused) | `DrawArcs`, `ScanTick`, `ShowRouteLine`, `PairKeyTick` |

`PairKeyTick` keeps its name from the 1.x pairing key, since the hand-built Event Graph calls it. It calls
`BPL_FDPairing.Tick`, which runs in order:
1. `BPL_FDLoad.RestoreJobs` (once per load);
2. `BPL_FDDispatch.Tick` (a pass every `TickSeconds` of game time);
3. `BPL_FDVoyage.BuildingsStep` and `RouteStep`;
4. `StandInClick`;
5. `PanelTick`, which creates the dock GUI once and calls its `Step`.

### Networks and storage

**Memberships** are stored in the dock's own `WorkDock.activeTradePartnerId`, which the colony save keeps. The mod
has no save file of its own.

```
stored = -(2 + x)
x < NetBase (2^22):   1.x value, x = the target's dock ID
x >= NetBase:         network value, packed = x - NetBase
packed bits:  30..28 unused | 27 paused | 26..18 memb 3 | 17..9 memb 2 | 8..0 memb 1
membership (9 bits):  8..7 unused | 6..5 role (0 both, 1 provide, 2 request) | 4..0 network ID (0 = empty)
```

- A dock can be in at most 3 networks; network IDs run from 1 to 31.
- All bit work is behind pure helpers in `BPL_FDNet`: `Unpack`, `Pack`, `With`, `WithPaused`. `loom_test.py` tests
  them against a Python model.
- Queries (`FreightDocks`, `Members`, `RequestersOf`, `ProvidersOf`, `InUse`) decode the docks' values on each call.
- **Building index:** `IndexBuildings` keeps every building by ID (`Buildings`) and the freight docks (`Docks`); it
  is rebuilt after a rescan, after buildings are placed, and every 30 s.

**Colony-wide data** (`BPL_FDStore`) is kept in the colony's event flags (`ArcoSystems.m_miscEventFlags`), one name
per entry, `fd.<key>=<value>`. Names ignore case, so capitals are stored escaped.

| Key | Holds |
|---|---|
| `ver` | The FreightDock version that last ran on the colony |
| `n<id>` | A network's name |
| `d<dockId>` | A dock's name |
| `j<providerId>` | A job (see Jobs across a reload) |
| `a<requesterId>` | A requester's demand ages |

**Migration** (`BPL_FDNet.Migrate`, once per load when the docks are known): each 1.x pair becomes the lowest free
network with both docks in the role "both"; a 1.x value whose target is gone becomes -1. A converted colony can't be
read by mod 1.x. A migrated dock with no input warehouses stops loading, since providing now requires them.

### Dispatch

`BPL_FDDispatch.Pass` runs every `TickSeconds` of game time:

1. **Upkeep:** a returned job is completed; a job whose provider and requester no longer share a network, or whose
   dock is gone, or whose ship has been gone for two passes, is cancelled. Either way loading stops and manifest
   goods still aboard move to the provider's delivered-goods store (`Park`).
2. **Shrink:** a loading job keeps at most what its requester still wants of each good; a job left empty is
   cancelled.
3. **Demand,** per `"<requester>|<good>"`: the unmet requests of the requester's output warehouses, less what is
   already unloaded at the dock, less every undelivered job's manifest. `DemandSince` records how long each has been
   open.
   - The unmet requests are the game's logistics deficits. A "Keep empty" warehouse reports none, so
     `KeepEmptyDeficits` works them out per slot: `minHold - count - inbound`.
   - An output warehouse shared by several requesting docks is one demand: each sees its deficit less what is
     already the others' (`DrawOn`), and a job given to one lowers the others' open demand (`Redraw`).
4. **Grow:** a job still loading takes on more of what its requester wants, if the hold and the inputs allow.
5. **Assign:** every idle provider with a ship is scored against every requester it shares a network with, and the
   best-scoring pair gets a job; this repeats until no pair scores above zero.
   - **Score:** the sum over goods of `units x (1 + age / 600 s)`, divided by the round-trip time, estimated as
     twice the straight-line distance at `ShipSpeed` plus 60 s.
   - **Supply:** free stock in the provider's input warehouses (`count - reservedForPickup`), everything aboard, and
     leftovers in its delivered-goods store that its own outputs don't want. Providing requires at least one input
     warehouse.
   - **Shared input warehouses** are pooled per warehouse and drawn down as jobs are given. What loading jobs have
     yet to fetch is taken out of the pool first (`Reserve`), since haulers reserve stock only as they set out.
   - **A warehouse that is both input and output** of a requesting dock keeps its request level: only stock above
     it is supply (`KeepsLevel`).
   - **Own wants:** a provider doesn't ship a good its own output warehouses still request.
   - **Off duty:** a provider whose crew is off duty (`OnDuty`) is offered only what needs no haulers.
   - **Minimum load** (`MeetsMinimum`): a job must carry at least the option's share of the smaller of the hold and
     the requester's full requests (the request levels, met or not: `AskedLevels`) for the goods this provider has.
     A part-filled request therefore brings no small top-up trip. It is waived once the oldest demand the job would
     meet has waited longer than the depart-after time (10 minutes with Never).
6. **Explain:** for each request left open, why nothing comes (`WhyNot`, shown in the requester's INCOMING), and for
   each provider left idle, why (`IdleWhy`): every reason that applies, one a line.

**Jobs** are kept on BP_MapLoad: `JobTo` (provider to requester), `JobGoods` (the manifest, per
`"<provider>|<good>"`), `JobState`.

**States** (`BPL_FDNet.SetState` is the only writer and logs each move as `State: dock <id> <from> -> <to>`):

| State | Meaning | Next |
|---|---|---|
| idle | No job | loading (`Give`) |
| loading | Haulers fetch the manifest | depart pending, or idle on cancel |
| depart pending | Ready, or sent with Deliver now; goods still being carried | outbound |
| outbound | Sailing to the requester | dwell |
| dwell | Delivered, waiting at the requester | homeward |
| homeward | Sailing home | returned |
| returned | Home; the next pass completes the job | idle |

### Loading and departure

`BPL_FDLoad.FreightTick` runs every `TickSeconds` for each dock with a job whose ship is berthed.

- **Request:** the manifest is written to the dock's `m_requiredEmbarkSupplies_dockSpecific`, its live requirement
  and its input slots, so the dock's workers fetch those goods. Each input slot's capacity is the request less the
  hold; the game turns away haulers beyond it.
- **A ship holds only its job's freight.** Anything else aboard, provisions aside, is parked in the dock's
  delivered-goods store each plan. Leftovers parked there that a job wants are boarded directly.
- **Stall:** a good no hauler has picked up for 20 s is cut to what has been got, and listed in the dock GUI as
  dropped ("no hauler came", or "no stock" when the inputs hold none). A good dropped this way is not offered again
  from that dock for 600 s (`BarFor`). A loading job left with nothing is cancelled.
- **Departure:** the ship leaves when the whole manifest is aboard, when the depart-after time has passed since its
  first freight came aboard, or on Deliver now. If goods are still being carried, departure is pending until they
  are aboard.
- **Short departures:** a ship that leaves with less than its manifest has the manifest cut to what is aboard
  (`Trim`), so the rest is open demand for other providers.
- **Off duty:** while the crew is off duty the stall and depart-after clocks wait, and the job doesn't grow.
- **Stevedores:** workers in a freight dock's worker slots get the Stevedore modifier; anyone who stops working at
  one loses it (`SyncStevedores`).
- **Clocks:** every persistent time is on the colony clock (`WorldTime.m_totalWorldTimeElapsed`), which stops when
  paused, runs with game speed and is saved.

### Voyage

The game's navigation can't be steered from Blueprint, so the mod uses a stand-in.

- **The real ship** stays berthed at home, hidden, with its collision disabled. The colony and the sea simulation
  keep treating it as berthed.
- **The stand-in** is a copy of the ship's zoomed-in model, moved along a spline course at `ShipSpeed` from the home
  berth to the requester's stand-off point. It turns in place at each end and bobs all the time.
- **On arrival** (`BPL_FDVoyage.VoyageArrive`) the freight moves from the real ship's hold into the requester's dock
  cargo (`m_stockpile_goodsFromSea`). The requester's workers unload it, which needs a ship assigned there: a dock
  without a ship has no workers.
- **The return:** after `DwellSeconds` the stand-in sails home, is removed, and the real ship is shown again.
- **Fallback:** if the stand-in can't be spawned, the trip becomes a timer.
- **Safeguards:** if the real ship leaves its berth during a voyage, the voyage ends and the ship is shown. Delivery
  goes to the dock the stand-in visited. Goods that couldn't be delivered come home and are parked.

### Jobs across a reload

- **Saved:** per job, `fd.j<provider>` holds the requester, the state, the clocks, the Deliver now flag, the dwell
  end, the manifest and the short-departure and dropped-goods notes; `fd.a<requester>` holds demand ages. They are
  written where they differ from what is stored, after each dispatch pass and `FreightTick` and at each voyage
  step.
- **Restored** (`BPL_FDLoad.RestoreJobs`, once per load, when the buildings are indexed and the load's rescan is
  done): each job comes back in its saved state. A sailing job sails on, its stand-in placed by the colony clock. A
  job whose provider, ship or requester is gone is dropped.
- **Not kept:** stall clocks restart, and the 600 s bar on a dropped good is lost.

### Routes

**Water map:** a grid of 100-unit cells (`CellSize`), which is 2 game tiles.

| Map | Holds |
|---|---|
| `Blocked` | Land cells (terrain blocks above water) and building cells |
| `Penalty` | Near-shore cells: passable, but they cost more |
| `DockZone` | Other docks' structures over the water, rebuilt when `Blocked` changes size |

**Building cells:** a building with grid tiles blocks the cells holding its full and floor tiles
(`GridActor.liveFootprint`); one without blocks its colliding bounds, or all its parts if none collide, provided they
reach the surface.

**Route planning** (`BPL_FDVoyage`):
- A route runs from the provider's stand-off point to its job's requester's, and is stored per provider dock
  (`RoutePts`, `RouteLen`). It is queued when a job is given (`RequestRoute`).
- Searches run a little each frame (`RouteStep`, 1 ms a frame): A* over cells with a binary heap, then the path
  pulled straight. A ship about to sail finishes its route at once (`PlanNow`).
- Routes keep `ClearanceCells` away from the shore, except near either end.

**Course** (`MakeCourse`): a voyage spline built from the route points, with rounded corners and a turn arc at each
end; it is fixed at departure.

**Rescan** (generated, `fdgen/routes/rescan.py`): the whole map is rebuilt in slices across frames by `ScanTick`.

| Phase | Work | Budget per frame |
|---|---|---|
| 1 | Terrain blocks | `ScanBudget` (500) block reads |
| 2 | Coast and penalty | `ScanBudget / 20` cells |
| 3 | Buildings | `ScanBudget / 50` buildings |
| 4 | Route check | One dock |

- It runs in one go at load (`ScanNow`) and then every `RescanSeconds` of real time, so also while paused.
- In phase 4, a route that now crosses a blocked cell, or is missing, is replanned; every route is replanned when
  `Blocked` changed size.
- **Placed buildings** don't wait for it. `WBP_FDPanel` binds `onBuildingSpawned` in Loom and queues the actor
  (`BPL_FDVoyage.BuildingSpawned`); `BuildingsStep` writes each settled, placed building into the live map
  (`BP_MapLoad.AddBuilding`, generated from the same builder as phase 3), at most 10 a frame. Half a second after
  the last one, the buildings are indexed again and only the routes that now cross something are replanned
  (`RecheckRoutes`). Buildings added in the last 2 minutes are written again into each new map when a rescan swaps
  it in (`ReaddBuildings`).
- **Demolitions** and terrain changes have no event and wait for the rescan.

### Display

- **Network arcs** (`BPL_FDPairing.NetworkArcs`): while a freight dock is selected, an arc to each dock it provides
  to and from each dock that provides to it, in the network's colour.
- **Hover highlights** (`Highlight`): hovering a network, a Provide or Request cell or a good in either GUI shows
  that network's arcs and pointers on the docks concerned: providers red (#E9594D), requesters blue (#71D0EA).
- **Network colours** (`BPL_FDNet.NetColor`): one per network ID, with red and blue left out.
- **Route line:** the course of the selected dock's ship, as flat spline meshes; nothing without a job.
- **Stand-ins:** hovering one shows its course; clicking one pans the camera to its home dock.
- **Toasts:** only for copy, paste and undo of memberships.

## The GUIs

### Dock GUI (`WBP_FDPanel`)

Shown for every selected freight dock, to the left of the game's dock window, in the window's own frame, background
and fonts. It hides the window's "Load resources onto ship" bar and supported-actions frames while shown, and, since
game 0.7.211, the ship frame's departure checklist with Send to sea (`EmbarkationList`) and the Auto-depart and Repeat
toggles (`autodepart_area`): a freight dock's ship never departs by the game's hand. The Harbormaster's dock list
(game 0.7.211) leaves freight docks out: their category (`HarbormasterCategory`, key `freightDock`) and rows
(`HarbormasterRow`) are collapsed, checked every 0.5 s (`HideInHarbor`). Content is
refreshed every 0.5 s of real time.

| Section | Shows |
|---|---|
| Title | The dock's name, with the game's pencil icon; a click renames it. The map button |
| NETWORKS | One line per membership: the network's number and name in its colour, then "provide" in red and / or "request" in blue. The tooltip names its providers and requesters. The button opens the network GUI |
| SHIP | The job's target (a link), the ship's state, the hold, the one-way trip time; Pause and Deliver now. Without a job: "Idle:" and the first reason, with the others in the tooltip. Notes for dropped goods and short departures |
| MANIFEST | Per good of the job: available to load, reserved, on the way here, on the ship, amount requested (`WBP_FDWantRow`) |
| THIS DOCK'S REQUESTS | For a requesting dock: per requested good its icon and the unmet amount, dimmed when met; tooltip "have/asked" |
| INCOMING | For a requesting dock: per wanted good, how much is still wanted, what is on its way and from where, or why nothing comes |
| AT DOCK | Goods in the dock's delivered-goods store |
| TARGET'S REQUESTS | The same display as THIS DOCK'S REQUESTS, for the job's target, leaving this dock's own job out |
| THIS DOCK'S INPUT | Free stock of the dock's input warehouses: per good its icon with the amount under it |

- **Request amounts** (`BPL_FDNet.RequestLevels`): asked is the sum of the request levels (`minHold`) in the dock's
  output warehouses, "Keep empty" ones included. Unmet is each warehouse's shortfall (its level less its stock and
  what haulers are bringing), less what is waiting at the dock or on jobs to it.
- **Copy and paste:** Ctrl+C on a freight dock copies its memberships, Ctrl+V pastes them onto another, Ctrl+Z
  undoes that paste while the dock is still shown.
- **Names** are kept in the colony's event flags and cut at 60 characters; an empty name restores the default.

### Network GUI (`WBP_FDNetPanel`)

Opened from the dock GUI, to its left. A table of networks 1 to the highest in use plus one:

| Column | Shows |
|---|---|
| Network ID | Number and name in the network's colour, with the pencil icon; a click renames it |
| Provide, Request | A checkbox for the selected dock, then the network's number of providers or requesters; the tooltip names them |
| Requested goods | Icons of what the network's requesters ask for, dimmed when no provider has the good whitelisted in an input warehouse. An input warehouse with no whitelist counts as taking everything |

A good's tooltip (`WBP_FDNetTip`) gives the requested and stocked amounts, "Requested by:" in blue and
"Provided by:" in red with the docks' names, or "No provider on this network" in grey. Past 3 memberships the other
rows' checkboxes are disabled.

### Network map (`WBP_FDMapPanel`)

Opened from the dock GUI's title row, above the game's dock window.
- **Terrain:** the whole world, water shaded by depth, land in one colour, drawn a few rows a frame into a render
  target; built cells over water are drawn as land.
- **Shown:** the hovered network, else all of the selected dock's networks. Each member dock is a marker, red
  providing and blue requesting; each provider's course to its job's target is drawn in the network's colour (the
  Routes box turns that off); ships under way are dots.
- **View:** the wheel zooms about the cursor, dragging pans, a double-click shows the whole world.

## Keys and logging

No key is bound in a release build beyond Ctrl+C, Ctrl+V and Ctrl+Z on a selected freight dock.

Development code stays in the project unhooked:
- `BPL_FDCheat.Tick` (F4: resources and the Freight Dock tech; F7: route overlays), hooked by one line in
  `WBP_FDPanel.Step`;
- the probes, switched by `BPL_FDNet.Probing()`, `Timing()` and `LoadProbing()`, all false;
- BP_MapLoad's debug functions (`DebugCells`, `LogPlans`, `LogLinks`, `LogDocks`, `LogNauticalDocks`,
  `LogFootprint`, `DebugSetup`), bound to no key.

**Log file:** `%LOCALAPPDATA%\Whiskerwood\Saved\Logs\modlog.txt`. Every FreightDock line carries `[FreightDock] `
after its timestamp. Log text must be ASCII: any other character turns the modlog into UTF-16. With the probes off it
carries the load line, each job state move, each batch of buildings added to the route map, and a few others.

## Setup

`Config/DefaultEditor.ini`, section `[Suzie]`, makes the game's fields writable from Blueprint. Restart the editor
after changing it; the Output Log shows one "Forced blueprint writable" line per entry.

```
+ForceBlueprintWritable=Stockpile.Slots
+ForceBlueprintWritable=ResourceStockpileSlot.count
+ForceBlueprintWritable=ResourceStockpileSlot.capacity
+ForceBlueprintWritable=ResourceCollection.counts
+ForceBlueprintWritable=WorkDock.m_requiredEmbarkSupplies_live
+ForceBlueprintWritable=WorkDock.m_inputStockpile
+ForceBlueprintWritable=WorkDock.m_stockpile_goodsFromSea
+ForceBlueprintWritable=NauticalRaftDock.m_raftLoadingState
+ForceBlueprintWritable=NauticalShip.State
+ForceBlueprintWritable=NauticalShipState.cargo
+ForceBlueprintWritable=WorkDock.activeTradePartnerId
+ForceBlueprintWritable=Prototype_Agent.m_state
+ForceBlueprintWritable=AgentState.modifierState
+ForceBlueprintWritable=AgentState.derived_carryCapacity
+ForceBlueprintWritable=AgentModifierState.activeModifiers_all
```

The live list is the one in `Config/DefaultEditor.ini`; check it there before relying on this copy.

Releasing to the Workshop is covered in [Publish to Workshop.md](Publish%20to%20Workshop.md).

## BP_MapLoad tunables

Defaults are as set on the class. `Tools/FreightDock/tests/blueprint_vars.json` lists every variable with its type.

| Variable | Default | Purpose |
|---|---|---|
| `TickSeconds` | 5 | Freight logic and dispatch interval (game time) |
| `MaxWaitSeconds` | 120 | Depart-after time; overwritten by the option |
| `MinLoad` | 0 | Minimum load share; overwritten by the option |
| `TripSeconds` | 30 | Fallback trip time (no stand-in) |
| `ShipSpeed` | 100 | Stand-in speed, units per second of game time |
| `TurnRate` | 45 | Turn-in-place speed, degrees per second |
| `DwellSeconds` | 5 | Stand-in wait at the requester |
| `StandOff` | 200 | Stop distance out from a berth |
| `HoverRadius` | 300 | Hover / click distance for a stand-in |
| `CellSize` | 100 | Route cell size |
| `ClearanceCells` | 1 | Distance kept from the shore, except near the ends |
| `MaxExpand` | 20000 | A* expansion limit |
| `CourseSpacing`, `CornerRadius` | 200, 500 | Spline point spacing and corner rounding |
| `TurnRadius`, `TightTurn1`, `TightTurn2` | 300, 0.6, 0.35 | Turn arc radius, and the tighter fallbacks as fractions of it |
| `RescanSeconds` | 20 | Rescan interval (real time) |
| `ScanBudget` | 500 | Rescan work per frame |

Constants in Loom: the waiting bonus's time constant (`BPL_FDDispatch.Tau`, 600 s), the trip overhead
(`Overhead`, 60 s), the bar on a dropped good (`BarFor`, 600 s), the route search budget
(`BPL_FDVoyage.RouteBudgetMs`, 1 ms), the settle and re-add times for placed buildings (`SettleSeconds` 0.25 s,
`ReaddSeconds` 120 s).

## Known limitations

- A course is fixed when the ship departs. A replan mid-voyage applies from the next trip.
- Each ship carries freight one way, and the return trip is empty.
- One ship per dock, and one job per ship at a time.
- A requesting dock needs a ship too: without one it has no workers, so goods delivered to it aren't unloaded.
- Ships always request canned food (provisions). With input warehouses set, the workers load provisions only if an
  input warehouse whitelists canned food.
- Demolitions reach the route map only at the next rescan, up to about 40 s later.
- The mod can't steer logistics whiskers: they may fill an output warehouse's request before a delivery arrives.
- The dock uses the trade dock's model.
