# Publishing FreightDock to the Steam Workshop

Whiskerwood (Steam app 2489330) has no in-game uploader; items are uploaded with SteamCMD. A Workshop item is a flat
folder holding `FreightDock.pak` and `FreightDock.uplugin`, the same pair Mod Tools installs locally. The game skips a
mod whose `.uplugin` lacks `"EngineVersion": "5.8"` or later (reason written to `modlog.txt`).

## Files

| Path | Role |
|---|---|
| `Content/Mods/FreightDock/FreightDock.uplugin` | Name, description, version, author shipped with the mod. Bump `Version` per release. |
| `Assets/Thumbnail.jpg` | Workshop preview image (Steam limit: under 1 MB). |
| `Tools/FreightDock/stage_workshop.ps1` | Copies the installed pak and uplugin into `Saved/Workshop/FreightDock/content/`. |
| `Tools/FreightDock/upload_workshop.ps1` | Writes `Saved/Workshop/FreightDock/FreightDock.vdf` and runs SteamCMD. |
| `Tools/FreightDock/readme_to_bbcode.py` | Converts `README.md` to Steam BBCode in `Saved/Workshop/FreightDock/description.txt`, to paste into the item's description: `uv run python readme_to_bbcode.py` (in `Tools/FreightDock`). |
| `Tools/FreightDock/workshop_id.txt` | The item's ID, written by the first upload. Keep it: without it the next upload creates a new item. |

## Releasing

1. Bump `Version` in `FreightDock.uplugin`.
   Check the F4 cheat and the loading probe are unhooked: no `BPL_FDCheat.Tick` or `BPL_FDCheat.Probe` call in `Step` of `UI/WBP_FDPanel.lm` (`BPL_FDCheat` itself stays, unused).
2. In the editor: right-click `Content/Mods/FreightDock` > **Cook & Install** (or `WWBlueprintToolset.CookAndInstall`, see `Tools/FreightDock/README.md`). Close the game first: it holds the installed pak open, so the install fails. Test in game.
3. Stage:
   `powershell -ExecutionPolicy Bypass -File Tools/FreightDock/stage_workshop.ps1`
   It warns if a mod asset was saved after the pak was cooked.
4. Upload:
   `powershell -ExecutionPolicy Bypass -File Tools/FreightDock/upload_workshop.ps1 -Account <steam login> -ChangeNote "1.0: first release"`
   SteamCMD asks for the password and Steam Guard code unless the login is cached.
   SteamCMD's default path is `C:\Program Files\steamcmd\steamcmd.exe`; pass `-SteamCmd <path>` otherwise.

## First upload

- The item is created **private**. On its Workshop page (link printed at the end): write the description, set the
  tag (Feature Addition), check the preview, then set visibility to Public.
- Uploading requires having accepted the Steam Workshop legal agreement; the item page shows a banner until then.
- Later uploads send title, preview, content and change note only, so the page description and visibility set on the
  Workshop page are kept.

## Checking a release

Subscribe to the item, move `%LOCALAPPDATA%\Whiskerwood\Saved\mods\FreightDock` out of the way so only the Workshop
copy can load, start the game and check `modlog.txt` for FreightDock's startup lines.
