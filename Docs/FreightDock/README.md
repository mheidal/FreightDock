
Frustrated with Logistics whiskers moving goods from island to island by paw across ferries, only one cartload at a time? So was I! This mod implements a new type of dock, the Freight Dock, which allows for finer control and higher throughput for your inter-island logistics.

Build two freight docks, pair one with the other using a new in-game hotkey, and add warehouses to one or both docks' "Deliver to" list. When `Dock A` is set to deliver to `Warehouse W`, and `Dock A` is paired with `Dock B`, the workers at `Dock B` will be tasked with loading whatever is requested at `Warehouse W` onto the ship at `Dock B`! When the ship's cargo hold is full, or has all of the goods requested at `Warehouse W`, or after a (configurable) timeout since the first item was loaded, the ship will depart for `Dock A`, stay there for a brief moment, and the goods will be deposited into `Dock A` for its workers to deliver to `Warehouse W`.

This can be bidirectional: docks A and B can both send one another goods, simply by connecting each to warehouses with requests.

If you restrict which warehouses a dock can pick up goods from, it will not try to load any goods which are requested on the far side but which are not stored in those warehouses.

Ships can be seen sailing between docks, following the shortest route from dock to dock! These routes and are rebuilt when buildings and terrain are added and removed.

Ships can be sent off early by a button on the dock's UI.

**Known limitations:**
- Both sides need to have a ship for deliveries to function, even if you only want one-way logistics. (The game doesn't allow you to assign workers to docks without ships.) Goods can be dropped off at a dock if that dock doesn't have a ship/workers assigned, but they will not be unloaded.
- The mod is not able to directly move the real ship assigned to a dock; instead, it makes that ship invisible and spawns a copy of the ship's model, which it moves. The mod gracefully handles ships being reassigned mid-delivery: it completes the delivery before making the real ship visible again at the dock where it's been reassigned.
- The dock's graphics are just a copy of the Trade Dock's.
- Ships always request canned food; I wasn't able to find a way to disable this request, even though freight dock ships shouldn't be sent between islands.

**Possible future work:**
- Many-to-many freight dock connections (receive from multiple, deliver to multiple!)

**AI Disclosure**
This mod was ideated and refined by feedback from myself, but its code was written in its entirety by Claude. I have tested its functionality to some degree, but I have not read the vast majority of its code (written as node-based Unreal Engine blueprint logic), so cannot provide guarantees as to how the mod works in every situation.

**License**
This mod is a fork of 

The thumbnail is an edit of the image "US Cargo Ship off McMurdo Station, Antarctica", sourced via Wikipedia.
By Vincent Clifton - Navy NewsStand Photo ID: 070204-N-0469C-004Navy NewsStand Home, Public Domain, https://commons.wikimedia.org/w/index.php?curid=3575871

