# Editor crash when re-saving a new source whose first build failed

**Loom:** LoomEditor 0.1.0 (plugin `Version` 1), Unreal Engine 5.8.0 (Whiskerwood modkit), Windows 11.

## Summary

When a new `.lm` file (no asset on disk yet) fails its first Blueprint compile, saving the file again crashes the editor with an assertion in `FKismetEditorUtilities::CreateBlueprint`.

## Steps to reproduce

1. With the editor open, create a new Blueprint function library source whose Blueprint compile fails. In my case `loom check` passed but the compile did not:

   ```loom
   blueprint BPL_Example : BlueprintFunctionLibrary at /Game/Example/BPL_Example

   fn Used() -> int {
       let used: set<int> = []
       used.Add(1)
       return used.Length()
   }
   ```

   The editor log shows:
   ```
   LogBlueprint: Error: [AssetLog] /Game/Example/BPL_Example.BPL_Example: [Compiler] Default value '' for  Used  is invalid: 'Set inputs (like 'Used') must have an input wired into them (try connecting a MakeSet node).'
   LogLoomBuild: Display: LoomBuild: failed, 1 errors, 7 Blueprints
   ```
   No `.uasset` is written to disk. The Blueprint stays in memory: the editor's autosave even wrote `/Temp/Autosaves/.../BPL_Example_Auto5`.

2. Fix the source (here, `array<int>` with `AddUnique`) and save it again.

## Expected

The existing in-memory Blueprint is rebuilt and saved.

## Actual

The editor crashes:

```
LogWindows: Error: appError called: Assertion failed: FindObject<UBlueprint>(Outer, *NewBPName.ToString()) == 0
[File:...\Engine\Source\Editor\UnrealEd\Private\Kismet2\Kismet2.cpp] [Line: 441]
```

## Likely cause

`LoomApplier.cpp` (around line 443) decides between "update" and "create" with `FPackageName::DoesPackageExist(PackagePath)`, which only checks disk. After a failed first build the package and Blueprint exist only in memory, so the second build takes the create branch. `CreateBlueprint` then finds a Blueprint of that name already in the package and asserts.

Suggested fix: before creating, look for the Blueprint in memory as well, for example `FindObject<UBlueprint>(FindPackage(nullptr, *PackagePath), *AssetName)`, and take the update path if it's there. Alternatively, discard the in-memory Blueprint and package when a first build fails.

## Related: `loom check` and empty set literals

`loom check` (and the MCP `check` tool) accepts `let x: set<int> = []`. The Blueprint compiler rejects it, because a Set input with no MakeSet wired in has no valid default. Either compile an empty set literal to a wired `MakeSet` node, or reject it in `check` so the error appears before the editor build.
