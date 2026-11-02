# Freight Dock

Frustrated with Logistics whiskers moving goods from island to island by paw across ferries, only one cartload at a time? So was I! This mod implements a new type of dock, the Freight Dock, which allows for finer control and higher throughput for your inter-island logistics.

## Features and how to use
Build two freight docks, pair one with the other using a new in-game hotkey, and add warehouses to one or both docks' "Deliver to" list. When `Dock A` is set to deliver to `Warehouse W`, and `Dock A` is paired with `Dock B`, the workers at `Dock B` will be tasked with loading whatever is requested at `Warehouse W` onto the ship at `Dock B`! 
When the ship's cargo hold is full, or has all of the goods requested at `Warehouse W`, or after a timeout since the first item was loaded, the ship will depart for `Dock A`, stay there for a brief moment, and the goods will be deposited into `Dock A` for its workers to deliver to `Warehouse W`.

To pair two docks, select one (so that its UI opens), press the hotkey (default `F5`), then select the other and press the hotkey again. To unpair two docks, select one, press the hotkey, then unselect it and press the hotkey again.

This can be bidirectional: docks A and B can both send one another goods, simply by connecting each to warehouses with requests.

Ships can be seen sailing between docks, following the shortest route from dock to dock! These routes are rebuilt periodically to account for the addition and removal of buildings and terrain. Routes are visible when a paired dock is selected.

Ships can be sent off early by a button on the dock's UI.

Whiskers assigned to a freight dock gain a new modifier, "Stevedore", granting +10 carrying capacity.

The hotkey to pair two docks defaults to `F5`. The timeout before a ship departs early is 120 seconds. Both are configurable in the game's Mods settings.

## Known limitations
Both sides need to have a ship for deliveries to function, even if you only want one-way logistics. (The game doesn't allow you to assign workers to docks without ships.) Goods can be dropped off at a dock if that dock doesn't have a ship/workers assigned, but they will not be unloaded.

The mod is not able to directly move the real ship assigned to a dock; instead, it makes that ship invisible and uninteractable and spawns a copy of the ship's model, which it moves.

The mod gracefully handles ships being reassigned mid-delivery: the delivery is immediately cancelled, the stand-in model is removed, and the ship is made visible and interactable at its new dock. The freight remains onboard the ship.

If a freight ship's journey is interrupted by a save-and-load, the stand-in will disappear and the ship will appear at its dock. It will not begin the journey again until its departure conditions are once again met (has all requested items OR cargo hold full OR timeout period exceeded (counting from load)).

This mod is unable to affect the decision-making of logistics whiskers; you may find that a freight delivery overfills a destination warehouse's request, since logistics whiskers could try to get to it first.

The dock's graphics are just a copy of the Trade Dock's.

Ships always request canned food; I wasn't able to find a way to disable this request, even though freight dock ships shouldn't be sent on nautical expeditions.


## Possible future work
Many-to-many freight dock connections (receive from multiple, deliver to multiple!)

To leave feedback or suggestions on the mod, please [create a new GitHub issue](https://github.com/mheidal/FreightDock/issues/new). You can also reach out to me on Discord `@notnot`.

## AI Disclosure
This mod was ideated and refined by feedback from myself, but its code was written in its entirety by Claude. I have tested its functionality to some degree, but I have not read the vast majority of its code (written as node-based Unreal Engine blueprint logic), so cannot provide guarantees as to how the mod works in every situation.

## License
This repository is a fork of [Buckminsterfullerene's Whiskerwood Project](https://github.com/Whiskerwood-Modding/Whiskerwood-Project), the Whiskerwood modkit. Many thanks for developing this handy tool! It uses the MIT License.

## Credits
Several mods were consulted to learn the structure of Whiskerwood mods; no data was directly borrowed from these mods. Thank you to the authors of those mods, including:
- [WhiskerChurch by MRemingtonB](https://steamcommunity.com/sharedfiles/filedetails/?id=3817728506)
- [Flagship by MRemingtonB](https://steamcommunity.com/sharedfiles/filedetails/?id=3809890598)
- [Fertilizer by rinku](https://steamcommunity.com/sharedfiles/filedetails/?id=3813028140)
- [WhiskerTraits by Fretmute](https://steamcommunity.com/sharedfiles/filedetails/?id=3673601103)

The thumbnail is an edit of the image "US Cargo Ship off McMurdo Station, Antarctica", sourced via Wikipedia.
By Vincent Clifton - Navy NewsStand Photo ID: 070204-N-0469C-004Navy NewsStand Home, Public Domain, https://commons.wikimedia.org/w/index.php?curid=3575871