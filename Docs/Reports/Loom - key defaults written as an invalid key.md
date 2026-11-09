# Key (FKey) defaults written by Loom come out as an invalid key "("

## Environment

- LoomEditor plugin 0.1.0 (`EngineVersion` 5.8.0); `loom.exe` dated 2026-11-02, SHA-256 starting `f546ea82719c9214`.
- Unreal Engine 5.8 (Whiskerwood modkit), Windows.

## Summary

A `Key` default written as Loom's only accepted Key literal, `Key(KeyName: "F4")`, passes `loom check` and builds without error, but the Blueprint ends up holding the key `"("`, which is not a valid key. At runtime, `Key_GetDisplayName` returns `"("` and `Key_IsValid` returns false.

This happens for every engine key, and for every place a Key default appears: variables, arrays and maps. Function parameters emit the same text but were not tested in the engine.

Cause: Loom writes Key defaults in the general struct text form, `(KeyName="F4")`. `FKey` has its own text import (`ImportTextItem`, enabled by `TStructOpsTypeTraits`), and that import expects the bare key name, `F4`.

## Repro

```loom
blueprint BP_KeyTest : Actor at /Game/Scratch/BP_KeyTest

var A: Key = Key(KeyName: "F4")
```

`loom check`: "1 source, ok". `loom build` emits:

```json
{"op": "variable", "name": "A", "type": "struct:/Script/InputCore.Key", "default": "(KeyName=\"F4\")"}
```

After applying it, the class default object holds `A = "("`.

## What Loom accepts and emits

| Source | `loom check` | Emitted `default` |
|---|---|---|
| `var A: Key = Key(KeyName: "F4")` | ok | `(KeyName="F4")` |
| `var A: Key = Key(KeyName: "NotAKey")` | ok (not validated) | `(KeyName="NotAKey")` |
| `var A: Key = Key(KeyName: "")` | ok | `(KeyName="")` |
| `var A: Key = Key()` | ok | `()` |
| `var A: Key` | ok | (none) |
| `var A: array<Key> = [Key(KeyName: "F4"), Key(KeyName: "F5")]` | ok | `((KeyName="F4"),(KeyName="F5"))` |
| `var A: map<string, Key> = {"cheat": Key(KeyName: "F4")}` | ok | `(("cheat",(KeyName="F4")))` |
| `fn F(k: Key = Key(KeyName: "F4"))` | ok | param default `(KeyName="F4")` (not tested in the engine) |
| `var A: Key = "F4"` | error: "expected a Key literal" | — |
| `var A: Key = Key("F4")` | error: "a value set here must be written out, such as 5, "text" or Vector(X: 1, Y: 2, Z: 3)" | — |
| `let k = Key(KeyName: "F4")`, a `return` of one, or one passed as a call argument, in a function body | error: "Key has no field KeyName that Blueprints can set" | — |

So the only accepted form is the struct literal, and it is accepted only as a default. Because a Key can't be made in a function body at all, a broken default leaves no way to get a working key from Loom code.

## Engine test: every key

**Method:**
1. Made a scratch Actor Blueprint.
2. Added one `Key` variable per entry of `EKeys` in `InputCoreTypes.h` (353 keys, from `A` and `F4` through gamepad, mouse, touch, gesture and every XR controller's keys), in three text forms each. The defaults were set through `FBlueprintEditorUtils::AddMemberVariable(Blueprint, Name, Type, Default)`, the same call `LoomApplier.cpp` makes for a `variable` op (line 851).
3. Compiled the Blueprint and read every value back from the class default object.

| Default text | Held after compiling |
|---|---|
| Bare name, e.g. `F4` (what the engine's own editor writes) | **353 / 353 correct** |
| `(KeyName="F4")`, Loom's form | **0 / 353**: all are `"("`, with no compiler message |
| `(KeyName=F4)`, unquoted | **0 / 353**: all are `"("` |
| `()` (Loom's `Key()`) | `"("` |
| `(KeyName="")` | `"("` |
| `(KeyName="NotAKey")` / bare `NotAKey` | `"("` / `"NotAKey"` |

Containers (Loom form against bare names):

| Default text | Result |
|---|---|
| `((KeyName="F4"),(KeyName="F5"))` (Loom's array) | `["("]`: one element, not two. Compiler warning: "Can't parse default value … Property: X_ArrayLoom" |
| `(F4,F5)` | `["F4", "F5"]` |
| `(("cheat",(KeyName="F4")))` (Loom's map) | `{}`: empty. Compiler warning: "Can't parse default value … Property: X_MapLoom" |
| `(("cheat",F4))` | `{"cheat": "F4"}` |

A plain Key variable fails silently: no compiler warning, so a wrong key is found only at runtime. Arrays and maps at least warn.

## Expected

`Key(KeyName: "F4")` gives the key F4. Equivalently, Loom emits `F4` as the default text for `/Script/InputCore.Key`: bare names alone, and bare names inside arrays and maps.

## Suggested fixes

1. **Emit the right text:** when writing a default for `struct:/Script/InputCore.Key`, write the `KeyName` value bare (`F4`, `(F4,F5)`, `(("cheat",F4))`). More generally, structs with a native `ImportTextItem` need their own text form instead of the `(Field=Value)` one.
2. **Accept a simpler literal:** for example `"F4"` or `Key("F4")` as a Key literal, since `KeyName` is private and the docs don't describe the form `Key(KeyName: …)`.
3. **Check key names:** optionally check them against `EKeys`. Today `Key(KeyName: "NotAKey")` passes the check.
4. **Make keys usable in functions:** allow a Key to be made in a function body (for example by lowering to a variable default or a `Conv_StringToKey`-style call where one exists), or say in the docs that Keys exist only as defaults.

## Workaround in use

After each Loom build of the source, set the variable's default to the bare name through the Blueprint variable API (or the Class Defaults panel) and recompile. The next Loom build of that source resets it to `"("`.
