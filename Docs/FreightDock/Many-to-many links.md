# Many-to-many dock links (tabled)

Status: investigated, not implemented. A persistence spike succeeded (2026-11-01). Its code is on branch `freightdock-packed-links-spike`. The shipped mod still links freight docks strictly one-to-one.

## Goal

Let a freight dock link to several other freight docks, not just one partner. A dock's ship would then serve several destinations.

## Current design (one-to-one)

- **Pairing storage:** stored in the game's own `WorkDock.activeTradePartnerId` (int32) as `-2 - partnerDockId`.
  - Paired means a value of -2 or below.
  - `-1` means unpaired, which is the game's own "no partner" value.
  - The game never sets values of -2 or below, so its own trade logic ignores them.
- **Persistence:** the field persists through the game's `.whisker` save format even though it has no `CPF_SaveGame` flag. The mod adds no save data of its own; every other piece of state is rebuilt on load.
- **Per-dock state:** all runtime state in BP_MapLoad is keyed by dock ID and assumes one partner per dock:
  - route curves and route splines (one route per source dock, toward its partner);
  - `Voyages` / `VoyageShip` / `VoyageSpline`;
  - `LoadingSince`, `RouteStart` / `RouteEnd` / `RouteValid`;
  - `PartnerOf`.

## Persistence spike: result

Question: can one int32 hold several links and still survive a save/load?

- **Test value:** `-(2 + (5 | 7<<6 | 9<<12 | 33<<18 | 62<<24))` = **-1048875463**. That is own slot 5, with links to slots 7, 9, 33 and 62.
- **Procedure:**
  1. `SpikeStorage` (run once, ~2 s after load) wrote the test value into an unpaired freight dock (11700).
  2. The game was saved and reloaded.
- **Result:** the reloaded dock read back -1048875463 exactly (`Packed spike: test value FOUND after load`). The existing pair (11769 ↔ 11691) was untouched. Route planning ran normally and nothing in the game reacted to the odd value.
- **Conclusion:** the full int32 range, at least up to 30 bits of payload, survives a save. Several links can be stored with no extra save data.

Spike code, all temporary:

- **Functions:** `SpikeStorage` and `SpikeTick`, both in `Tools/FreightDock/fdgen/features/spike.py` and in BP_MapLoad. `SpikeTick` is hooked at the end of the `PairKeyTick` chain (… → DeliverTick → SpikeTick) in `features/options.py`.
- **Variable:** `SpikeFrames`.
- **Removing it:** see the docstring of `spike.py`. An earlier attempt at PlayState storage failed with "no HoldingsManagerComponent", a scenario-map-only system. Its helpers were deleted in the fdgen refactor.
- **Test dock:** the test save's dock 11700 still holds the test value. The current mod sees it as "paired" with a partner that doesn't exist. To clear it, press F5 on that dock, then F5 with no dock selected.

## Proposed storage format

Freight docks get small, stable **slot numbers** (1–63). The mod's IDs for docks are too large (~11000+) to pack several of them into one int.

```
stored = -(2 + packed)
packed bits:  30      | 29..24 | 23..18 | 17..12 | 11..6  | 5..0
              format  | link 4 | link 3 | link 2 | link 1 | own slot
```

- **Own slot:** 6 bits, 1–63; 0 = not yet assigned.
- **Links:** each link slot is 6 bits, holding the partner's slot number; 0 = empty.
- **Format bit:** bit 30 marks the new format. Old values (`-2 - dockId`, with dock IDs well under 2^30) are recognised by its absence and converted on load.
  - With the flag set, `packed` can reach 2^31 - 1, and `-(2 + packed)` would overflow int32. The fix is to keep the top link slot ≤ 62 when all other bits are set, or simply cap slots at 62.
- **Who stores a link:** only one end, the dock with the lower slot number or whichever end has a free link slot. That end-choice rule decides the real per-dock limit.
  - If each link is stored on exactly one end, a dock can have more than 4 links: up to 4 it stores itself plus any number stored by its partners.
  - The simpler rule "a dock stores all of its own links" caps each dock at 4.
- **Alternative layout:** 5 + 5 bits. That allows up to 31 freight docks and 5 stored links each.
- **Limits:** 63 freight docks per map. When a 64th is built it can't link; the mod shows a toast.

### On load

1. Read every freight dock's value.
2. For each new-format value, take the own slot and record it in a slot → dock map. Give every freight dock without a slot the next free slot and write it back.
3. Convert each old-format pair into one link between the two docks' slots.
4. Build the in-memory link list (dock-ID pairs) from all link fields, removing duplicates. Ignore, or drop, links to slots that no longer exist (e.g. a dock that was demolished).

### Bit operations in Blueprint

- KismetMathLibrary has `And_IntInt` / `Or_IntInt`. Int32 shift nodes have not been checked in this modkit.
- Multiply or divide by powers of 64 with `%` (`Percent_IntInt`) works regardless. Values stay non-negative inside `packed`, because the negation happens only at the storage boundary.
- Put pack and unpack in two pure helper functions, `PackLinks(Own, L1..L4) -> Int` and `UnpackLinks(Int) -> Own, L1..L4, IsNew`, so that nothing else touches bits.

## Alternative format: network membership (preferred direction)

The slot format's limits (63 docks, about 4 links per dock) were themselves a large part of why this was tabled. With networks, a dock stores **which networks it belongs to**, never which docks it links to. That removes the per-map dock limit and the per-dock link limit.

- A dock can **provide** on some networks and **request** on others.
- Every provider on network N supplies every requester on N.
- Example: dock A provides on 1; dock B requests on 1 and provides on 3; dock C requests on 3. The result is a chain, A → B → C.

### Bit budget

- The stored value must stay ≤ -2, which leaves about 31 bits of payload (`stored = -(2 + packed)`).
- One bit (bit 30) flags the new format, so that old `-2 - partnerId` values can be recognised and converted. That leaves **30 usable bits**.
- Two 16-bit IDs (2^16 networks each) would need 32 bits, which don't fit. The split is 15 + 15.

### Layouts

| Layout | Bits | Networks | Memberships per dock | Can express | Cannot express |
|---|---|---|---|---|---|
| **ID** | provider ID (15) + requester ID (15); 0 = none | 32,767 per role | 1 provide + 1 request | Fully connected provider→requester groups, chains, fan-out and fan-in trees | A dock in two different requester sets. Example: A→B, A→C and D→C without D→B. If D joins A's network to reach C, it also reaches B. |
| **Mask** | 15 provide bits + 15 request bits | 15 | Any subset | All of the above plus overlapping groups. The example above works with A providing {1,2}, B requesting {1}, C requesting {2}, D providing {2}. | More than 15 distinct networks per map |
| **Hybrid** (example) | 3 provider slots + 3 requester slots, 5 bits each | 31 | Up to 3 + 3 | Most overlapping layouts | More than 3 memberships per role |

Assessment: 15 networks with free membership (mask) probably covers real colonies better than 32,767 networks with one membership each (ID). This is a judgement call, not a tested conclusion.

### Bit access

- **Mask:** bit k is set if `(packed / 2^k) % 2 == 1`. To set or clear it, add or subtract `2^k`, or use `And_IntInt` / `Or_IntInt`.
- **ID:** `provider = packed % 32768`, `requester = (packed / 32768) % 32768`.

Either way, keep it behind pure helpers: `UnpackNetworks(Int) -> Provide, Request, IsNew` and `PackNetworks(...) -> Int`.

### On load

1. Read every freight dock's value and decode its memberships.
2. Convert each old one-to-one pair (A ↔ B) into one fresh network. Both docks provide and request on it, which keeps today's two-way behaviour.
3. Build, per network, the list of provider docks and requester docks. The working links are the provider × requester pairs, excluding a dock paired with itself.

### Compared with slot links

- **Removed:**
  - slot assignment and its 63-dock cap;
  - the 4-link cap;
  - the rule for which end of a link stores it;
  - stale links to demolished docks: a demolished dock just stops contributing.
- **Unchanged:**
  - **Destination choice:** a provider with several requesters still needs a rule.
  - **Return trips:** the open question remains.
  - **Routes:** they become per provider–requester pair. A network with p providers and r requesters needs p × r routes, so a large network multiplies A* and rescan work.
  - **Scope:** roughly the same ~30 functions still need rework (see Costs).
- **New: UI.**
  - **The problem:** F5 click-pairing doesn't fit network membership.
  - **What's needed:** the dock panel needs a provide/request network picker. That is a number entry for the ID layout, or a row of toggles for the mask layout.
  - **How:** inject it into the ShipPreparationWidget's VerticalBox like the Deliver now button (`InjectDeliverButtons`), and poll its controls the same way (`DeliverTick`).
  - **Trade-off:** more UI work than F5 toggling, but much easier for players than pairing docks one by one.
  - **Visualising:** the arcs of the selected dock's networks could be drawn in per-network colours.

## Costs

Rough scope: about 30 of the 76 BP_MapLoad graph functions would change.

### Functions affected (bpgen.py names)

| Area | Functions | Change |
|---|---|---|
| Storage | `set_partner`, `flip`, `partner_of` / PartnerOf, `unpair` / Unpair, `log_links` | Replace with link-list add/remove/query and pack/unpack helpers |
| Load | `RegisterExtras` or a new `LoadLinks` | Assign slots, convert old pairs, build link list |
| Pairing input | `PairAtCursor`, `ReadPairKey` | Toggle one link; F5 → nothing removes all links of the pending dock; toasts "Linked" / "Unlinked" / "Unlinked all" / "Link limit reached" |
| Routes | `PlanRoute`, `RouteCurve`, `DropRouteCurve`, `MakeCourse`, `BuildRouteLine`, `RouteStillClear`, `ScanRouteStep`, `DebugCells` | Key routes by link (A,B) instead of source dock. Rescan replans every link touching changed cells |
| Voyages | `FreightTick` (hand-built graph, no install spec), `StartVoyage`, `VoyageTick`, `VoyageArrive`, `WaitHeading`, `PreviewCourse`, `StandInClick` | Choose destination per departure; voyage state records destination |
| Loading / UI | `DeliverSelected`, `InjectDeliverButtons`, `IsFreightDock`, MaxWait handling | "Paired" test becomes "has ≥1 link"; Deliver now picks a destination via the same rule |
| Arcs | `DrawArcs`, `PairArcs`, `DrawRoute` | Draw all links of the selected dock. Each route arc needs per-link `RouteStart`/`RouteEnd`/`RouteValid` (now per dock) |

`FreightTick` has no install spec in bpgen.py. It was edited in place with BlueprintTools, so it would either need a full spec written first or be rewritten.

### Variables affected

These maps are keyed by dock ID: `PartnerOf`, route curves/splines, `RouteStart`/`RouteEnd`/`RouteValid`, `Voyages`, `VoyageShip`, `VoyageSpline`, `LoadingSince`.

- **Routes:** these become link-keyed. A link key can be one int: `slotA * 64 + slotB` with A < B, or the two dock IDs combined.
- **Voyage state:** this stays dock-keyed (one ship per dock), plus a new `VoyageDest` map.

### Risk

- **Rewiring:** most of the pairing and route plumbing is rewired at once. That cuts into the reliability work already done: footprint blocking, course fallbacks, rescan slicing and the stand-in hover route.
- **Bugs that look like success:** a bug in slot assignment or migration could silently break existing saves' pairs. Migration needs its own test: an old one-to-one save loads, converts, saves, and reloads.
- **Cost of rescans:** rescans multiply by link count. Each link has its own A* route, so with n docks fully linked there are n(n-1)/2 routes. Slicing across frames still applies, but the total work grows.

## Open design decisions (unresolved)

These were the blocking questions when the work was tabled. The first is new; the rest apply to both the slot format and the network format.

0. **Storage model.** Slot links or network membership? Networks are preferred because the slot format's capacity was too low. For networks, choose the ID, mask or hybrid layout.

1. **Destination choice.** When a dock has several links, where does its ship go?
   - (a) Round-robin through its links. Simplest.
   - (b) The partner with the greatest need for the loaded cargo. Needs a demand measure per resource.
   - (c) One ship per link. Changes the "one real ship per dock" model the stand-ins are built on.
2. **Return trips.** Does the ship return home after each delivery, as it does now? Or does it continue to the next link (a circuit), which complicates loading and unloading?
3. **Link limit.** Should the 6/6 layout (63 docks, 4 stored links) or the 5/5 layout (31 docks, 5 links) be used? Also, should each link be stored on one end or both?
### Reference: Factorio's LTN mod

The network design converged on the approach of LTN (Logistic Train Network), a Factorio mod. LTN's network ID is a 32-bit mask, the same idea as the mask layout above. Its answers to the questions above are worth borrowing:

- **Destination choice:** demand-driven (option (b) above). A requester places a request when its stock falls below a per-stop threshold. A central dispatcher then pairs it with a provider on a shared network that has enough of the item, and sends one vehicle with exactly that delivery.
- **Return trips:** vehicles return to a depot after every delivery, and the dispatcher only uses idle vehicles at depots. FreightDock's ships already return to their home dock, which acts as the depot.
- **Thresholds:** each stop sets its own request and provide thresholds, and deliveries below them aren't dispatched. This stops wasteful trips with small loads. The nearest FreightDock equivalents are the "depart after" option and Deliver now. Per-dock thresholds would sit in the same network-picker UI.

FreightDock remains its own design: ship stand-ins, A* water routes and dock panels. LTN is a reference for dispatch rules, not a template.

4. **Interaction cost.** F5 toggling is cheap to build but becomes awkward for a dock with many links. Removing a single link means selecting both ends. "Remove all" is F5 → F5 on empty ground.

## If resumed

1. Remove the spike code: the functions, `SpikeFrames`, the `PairKeyTick` hook and the bpgen.py leftovers listed above.
2. Decide the open questions above.
3. Write the pack and unpack helpers (`PackLinks`/`UnpackLinks` or `PackNetworks`/`UnpackNetworks`), and a load-time `LoadLinks` with old-format migration. Test migration on a one-to-one save before touching anything else.
4. Swap the storage layer (`partner_of`, `unpair`, `set_partner` callers) for a link list, keeping one link per dock at first. Behaviour should be identical to today's; this is a refactor checkpoint.
5. Move routes to link keys, then voyages and destination choice, then arcs and the pairing UI.
6. Run the full regression: pair and unpair, building over a route, mass-build rescan, Deliver now, depart timeout, stand-in hover route, and save/load.
