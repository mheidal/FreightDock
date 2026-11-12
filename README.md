# Freight Dock

Frustrated with Logistics whiskers moving goods from island to island by paw across ferries, only one cartload at a time? So was I! This mod implements a new type of dock, the Freight Dock, which allows for finer control and higher throughput for your inter-island logistics.

## How to use
This mod adds a new building, the Freight Dock. Freight Docks deliver goods to one another according to supply and demand. This mod has a concept of joining "networks", labels you can apply to docks. Freight Docks can join a network as a provider, a requester, or both; the mod will schedule delivery jobs from providers to requesters which are part of the same network.

Freight Docks have an associated UI panel which opens when the dock is selected. That panel has a sub-panel, the "Freight Networks" UI, accessible via the "Edit networks" button in the "Networks" section of the Freight Dock UI. There, the player can use the checkboxes to choose which networks the dock provides to and requests from. A dock can be part of up to 3 networks; there can be at most 31 networks in a single colony.

To create supply and demand within a freight network, the user must link a freight dock to warehouses in the game's native dock GUI's Logistics tab, with the "Pick up from" and "Deliver to" buttons. These link "input" and "output" warehouses, respectively.

Requests set for individual goods in docks' linked output warehouses determine what goods are delivered from providers to requesters, and in what quantity. A provider will try to deliver as much as it can per delivery, limited by the amount it has stocked and the size of its ship's cargo holds. The mod considers providers to be able to provide any goods whitelisted in their input warehouses.

Docks can both send and receive goods. To send goods, the dock must be connected to at least one input warehouse and be marked as a provider on at least one network; to receive goods, the dock must be connected to at least one output warehouse and be marked as a requester on at least one network. Two docks can send deliveries to one another if both are marked as being both provider and requester on their shared network(s).

### Example of use
To make deliveries between two docks, from `Dock A` to `Dock B`, set them to be members of the same freight network (`Network 1`, say). Add `Dock A` to `Network 1` as a provider, and add `Dock B` to `Network 1` as a requester. Link `Dock A` to an input warehouse `W1` which contains a particular good (`Stone`, say) and link `Dock B` to an output warehouse `W2` which has a request for that same good.

The mod's job scheduler will create a job which delivers `Stone` from `Dock A` to `Dock B`. The whiskers at `Dock A` will pick up `Stone` at `W1` and deliver it to `Dock A`, where it will be loaded onto the ship. When the whiskers have gathered all goods scheduled to be delivered (or when departure is otherwise triggered, see **Settings**), the ship at `Dock A` will sail to `Dock B` and unload the goods there. The whiskers at `Dock B` will unload the goods from `Dock B` to `W2`.

### Features
Scheduled deliveries can contain multiple types of goods, so long as they are held by the provider's input warehouses and requested by the requester's output warehouses.

The Freight Dock UI panel shows the dock's freight network information: the dock's name, the status of its ship, its requests (if any), its input goods (if any), and the manifest for an assigned job, as well as the fulfillment levels of that job's target's requests. From this panel, the user can open the minimap (see below), open the Freight Network UI panel, pause the dock so it will not take future jobs, and cause the ship to immediately embark to complete its job, not waiting for more goods to be loaded.

The mod can display a minimap showing the position of every Freight Dock within some network(s), their roles as providers or requesters, and the routes that active jobs will take.

Ships can be seen sailing between docks, following the shortest route from dock to dock. These routes are rebuilt periodically to account for the addition and removal of buildings and terrain. Routes are visible when a dock with an assigned job is selected, or when hovering over a freight dock's ship in motion. Routes react and are rebuilt faster in response to construction than destruction of buildings.

Docks and networks can be renamed from their respective UI panels.

Whiskers assigned to a freight dock gain a new modifier, "Stevedore", granting +10 carrying capacity.

The Freight Dock is unlocked by a tier-1 research, available to research alongside the other dock types.

Copy-pasting settings between Freight Docks will copy network memberships from one to the other.

Several docks can share input or output warehouses.

### Migration
The mod is backwards compatible with 1.x save files; paired docks are converted to the pair both being set to provide and request on an exclusive network.

### Warnings
The freight system implemented by this mod is fairly fragile, being dependent on many factors out of its control. Each dock's GUI tries to communicate to the player reasons why docks are idle or goods aren't being delivered. This detection system has a lot of edge cases. Please send me a bug report with details if you run into one.

Both sides need to have a ship for deliveries to function, even if you only want one-way logistics. (Whiskerwood doesn't allow you to assign whiskers to docks without ships.) Goods can be dropped off at a dock if that dock doesn't have a ship/whiskers assigned, but they will not be unloaded.

This mod is unable to affect the decision-making of logistics whiskers; you may find that a freight delivery overfills a destination warehouse's request, since logistics whiskers could try to get to it first. Freight Dock allows deliveries to warehouses with "Keep Empty" set, which will prevent logistics whiskers from filling output warehouses.

In rare cases (the demolition of a requester dock mid-voyage, for example), a ship will be unable to unload its goods, and will return to its home dock full. The goods will be unloaded into the dock, and can be stored from there or reused in a future delivery.

Freight Docks will not ship goods from their input warehouses if they're also requested at that dock's output warehouses.

If a provider dock fails to pick up any goods for 20 seconds while loading its ship (for example, if the input warehouse is unreachable), the goods will be marked as stalled. The provider will not offer them for 10 minutes afterwards.

## Settings 
The mod provides two settings which modify behavior. The first is a maximum-load-time limit: setting "Depart After" to `N` seconds means that the dock will allow whiskers to load goods for a job for `N` seconds after , but if the job's manifest is not satisfied after that period, the ship will automatically depart. The mod provides the values `120s`, `180s`, `240s`, or `Never`. With the setting set to `Never`, the ship will not automatically depart until its manifest is satisfied.

The second setting is a minimum load requirement, which is a function of each ship's hold. The user can set a minimum load of `X%`, which will cause docks to reject possible jobs which would fill the ship's hold to less than `X%` capacity. For example, if `Dock P` has a ship `Ship S` with a cargo capacity of `144`, and provides `Flax` from `W1`, and `Dock R` requests `100 Flax` at `W2`, and the minimum load setting is set to `50%`, then `Dock P` will not be assigned a job to deliver `Flax` unless the job would deliver `72 Flax` or more.

There is a special case for the minimum load setting: If `Dock R` has a request set for `Q` `Flax`, and `Q` is less than `X%` of `Ship S`'s cargo capacity, then the job will only be assigned to `Dock P` if the amount to be delivered is at least `X%` of `Q`. To continue the above example, if `Ship S` has a cargo capacity of `144`, the minimum load setting is `50%`, and `Dock R`'s output warehouse `W2` has a total request for `50 Flax`, then `Dock P` will not be assigned a job to deliver `Flax` unless the job would deliver `25 Flax` or more. 

In other words, if `W2` requests `50 Flax` and holds `40 Flax`, then `Dock P` will not be assigned a job to deliver the last `10 Flax`.

Even with the minimum load setting preventing a job from being assigned, a request which has not been served for at least the depart-after setting's period (10 minutes when set to `Never`) will be served anyway.

## Technical limitations
The mod is not able to directly move the real ship assigned to a dock; instead, it makes that ship invisible and uninteractable and spawns a copy of the ship's model, which it moves.

The mod gracefully handles ships being reassigned mid-delivery: the delivery is cancelled, the stand-in model is removed, and the ship is made visible and interactable at its new dock. The freight is unloaded at the ship's initial dock.

The dock's graphics are just a copy of the Trade Dock's.

Ships always request canned food; I wasn't able to find a way to disable this request, even though freight dock ships cannot be sent on nautical expeditions. The player can prevent the loading of provisions by always assigning input warehouses which do not whitelist canned food to docks.

Docks can only be members of at most 3 networks.

## Possible future work
- Refinement of Freight Dock UX and legibility
- Unique art for the Freight Dock
- Additional features such as provider/requester priority

To leave feedback or suggestions on the mod, please [create a new GitHub issue](https://github.com/mheidal/FreightDock/issues/new). You can also reach out to me on Discord `@notnot`.

## AI Disclosure
This mod was ideated and refined by feedback from myself, but its code was written in its entirety by Anthropic's Claude Code. I have tested its functionality to some degree, but I have not read the vast majority of its code, so cannot provide guarantees as to how the mod works in every situation.

## License
This repository is a fork of [Buckminsterfullerene's Whiskerwood Project](https://github.com/Whiskerwood-Modding/Whiskerwood-Project), the Whiskerwood modkit. Many thanks for developing this handy tool! It uses the MIT License.

## Credits
Much of this mod is written in the Unreal Engine scripting language Loom, created by pierrekin.

The design, philosophy, and mechanics of the many-to-many delivery system were inspired by the Factorio mods [Logistic Train Network by Optera](https://mods.factorio.com/mod/LogisticTrainNetwork) and [Project Cybersyn by lesbian_mami](https://mods.factorio.com/mod/cybersyn); many thanks to those excellent projects.

Several mods were consulted to learn the structure of Whiskerwood mods; no data was directly borrowed from these mods. Thank you to the authors of those mods, including:
- [WhiskerChurch by MRemingtonB](https://steamcommunity.com/sharedfiles/filedetails/?id=3817728506)
- [Flagship by MRemingtonB](https://steamcommunity.com/sharedfiles/filedetails/?id=3809890598)
- [Fertilizer by rinku](https://steamcommunity.com/sharedfiles/filedetails/?id=3813028140)
- [WhiskerTraits by Fretmute](https://steamcommunity.com/sharedfiles/filedetails/?id=3673601103)

The thumbnail is an edit of the image "US Cargo Ship off McMurdo Station, Antarctica", sourced via Wikipedia.
By Vincent Clifton - Navy NewsStand Photo ID: 070204-N-0469C-004Navy NewsStand Home, Public Domain, https://commons.wikimedia.org/w/index.php?curid=3575871

The mod can be downloaded via [the Steam Workshop for Whiskerwood](https://steamcommunity.com/sharedfiles/filedetails/?id=3832191059). Its source code is public [on Github.](https://github.com/mheidal/FreightDock)