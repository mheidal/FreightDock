"""Run tests of the Loom libraries' pure functions with Loom's test commandlet (headless editor).

    uv run python loom_test.py

Cases are built here, with expected values from a Python model of the same encoding, written to
.build/loomtest/<library>.json, and run with `UnrealEditor-Cmd -run=LoomTest`. Only pure functions are tested:
the commandlet calls them on the class default object, with no world. Takes a minute or so (editor start-up).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EDITOR = Path("C:/Program Files/WhiskerwoodEngine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe")
PROJECT = ROOT / "Whiskerwood.uproject"
OUT = HERE / ".build" / "loomtest"

# --- reference model of BPL_FDNet's encoding (see Docs/FreightDock/Many-to-many links.md)
BASE, PAUSED, SLOTS = 1 << 22, 1 << 27, 3
UNUSED = (1 << 30) | (1 << 29) | (1 << 28) | sum(3 << (9 * s + 7) for s in range(SLOTS))


def stored_of(packed):
    return -(BASE + packed) - 2


def pack(nets, roles, paused=False):
    packed = PAUSED if paused else 0
    slot = 0
    for net, role in zip(nets, roles):
        if slot < SLOTS and 1 <= net <= 31 and 1 <= role <= 3:
            packed += ((0 if role == 3 else role) * 32 + net) << (9 * slot)
            slot += 1
    return stored_of(packed)


def with_unused(stored):
    """stored with every unused bit set (30..28, each membership's bits 8..7), as a later version may write."""
    return stored_of((-stored - 2 - BASE) | UNUSED)


def unpack(stored):
    x = -stored - 2 if stored <= -2 else -1
    is_new = x >= BASE
    packed = x - BASE if is_new else 0
    found = []
    if is_new:
        for i in range(SLOTS):
            m = (packed >> (9 * i)) & 511
            net, role = m % 32, (m // 32) % 4
            if net:
                found.append((net, role or 3))
    found.sort(key=lambda t: t[0])
    found = (found + [(0, 0)] * SLOTS)[:SLOTS]
    nets, roles = [f[0] for f in found], [f[1] for f in found]
    paused = is_new and bool(packed & PAUSED)
    old = x if 0 <= x < BASE else -1
    return nets, roles, paused, is_new, old


def arr(xs):
    return "(" + ",".join(str(x) for x in xs) + ")"


def b(x):
    return "True" if x else "False"


def net_cases():
    cases = []

    def pack_case(name, nets, roles, paused=False):
        cases.append({"name": name, "call": "Pack",
                      "args": {"Nets": arr(nets), "Roles": arr(roles), "Paused": b(paused)},
                      "expect": {"return": str(pack(nets, roles, paused))}})

    def unpack_case(name, stored):
        nets, roles, paused, is_new, old = unpack(stored)
        cases.append({"name": name, "call": "Unpack", "args": {"Stored": str(stored)},
                      "expect": {"Nets": arr(nets), "Roles": arr(roles), "Paused": b(paused), "IsNew": b(is_new),
                                 "OldTarget": str(old)}})

    pack_case("pack one", [1], [3])
    pack_case("pack three", [3, 7, 31], [1, 2, 3])
    pack_case("pack paused", [5], [2], True)
    pack_case("pack none", [], [])
    pack_case("pack skips bad entries", [0, 32, 4, 9], [1, 1, 0, 2])
    pack_case("pack drops a fourth", [1, 2, 3, 4], [1, 1, 1, 1])
    pack_case("pack maximum", [31, 31, 31], [3, 3, 3], True)

    unpack_case("unpack unpaired -1", -1)
    unpack_case("unpack zero", 0)
    unpack_case("unpack 1.x pair", -2 - 12126)
    unpack_case("unpack 1.x pair to dock 0", -2)
    for nets, roles, paused in ([[1], [3], False], [[3, 7, 31], [1, 2, 3], False], [[], [], True],
                                [[31] * 3, [3] * 3, True], [[9, 2], [1, 2], False]):
        unpack_case(f"unpack {nets} {roles} {paused}", pack(nets, roles, paused))
    unpack_case("unpack ignores unused bits", with_unused(pack([3, 7, 31], [1, 2, 3])))
    unpack_case("unpack reads role 3 as both", stored_of((3 * 32 + 5) | (1 * 32 + 9) << 9))
    unpack_case("unpack highest 1.x dock ID", -2 - (BASE - 1))
    unpack_case("unpack lowest network value", stored_of(0))
    unpack_case("unpack largest network value", stored_of(UNUSED | PAUSED | sum((2 * 32 + 31) << (9 * s) for s in range(SLOTS))))

    s = pack([3, 7], [1, 2])

    def one(name, call, args, ret):
        cases.append({"name": name, "call": call, "args": args, "expect": {"return": ret}})

    one("role on member", "RoleOn", {"Stored": str(s), "Net": "7"}, "2")
    one("role on non-member", "RoleOn", {"Stored": str(s), "Net": "4"}, "0")
    one("role on net 0", "RoleOn", {"Stored": str(s), "Net": "0"}, "0")
    one("role both is 3", "RoleOn", {"Stored": str(pack([9], [3])), "Net": "9"}, "3")
    one("role 3 read as both", "RoleOn", {"Stored": str(stored_of(3 * 32 + 9)), "Net": "9"}, "3")
    one("provides", "Provides", {"Stored": str(s), "Net": "3"}, "True")
    one("requester doesn't provide", "Provides", {"Stored": str(s), "Net": "7"}, "False")
    one("requests", "Requests", {"Stored": str(s), "Net": "7"}, "True")
    one("both requests", "Requests", {"Stored": str(pack([9], [3])), "Net": "9"}, "True")
    one("1.x value is no member", "IsMember", {"Stored": str(-2 - 12126)}, "False")
    one("member", "IsMember", {"Stored": str(s)}, "True")
    one("empty new value is no member", "IsMember", {"Stored": str(pack([], []))}, "False")
    one("with paused", "WithPaused", {"Stored": str(s), "Paused": "True"}, str(pack([3, 7], [1, 2], True)))
    one("with paused clears unused bits", "WithPaused", {"Stored": str(with_unused(s)), "Paused": "False"}, str(s))
    one("paused", "IsPaused", {"Stored": str(pack([3], [1], True))}, "True")
    one("not paused", "IsPaused", {"Stored": str(s)}, "False")
    one("pause without networks", "WithPaused", {"Stored": "-1", "Paused": "True"}, str(pack([], [], True)))

    def with_case(name, stored, net, role, ok, result):
        cases.append({"name": name, "call": "With", "args": {"Stored": str(stored), "Net": str(net), "Role": str(role)},
                      "expect": {"Ok": b(ok), "return": str(result)}})

    with_case("with adds", s, 9, 3, True, pack([3, 7, 9], [1, 2, 3]))
    with_case("with changes a role", s, 7, 3, True, pack([3, 7], [1, 3]))
    with_case("with removes", s, 3, 0, True, pack([7], [2]))
    with_case("with removes a non-member", s, 4, 0, True, s)
    three = pack([1, 2, 3], [1, 1, 1])
    with_case("with refuses a fourth", three, 5, 1, False, three)
    with_case("with refuses net 32", s, 32, 1, False, s)
    with_case("with refuses role 4", s, 3, 4, False, s)
    with_case("with replaces a 1.x pair", -2 - 12126, 2, 3, True, pack([2], [3]))
    with_case("with keeps paused", pack([3], [1], True), 4, 2, True, pack([3, 4], [1, 2], True))
    with_case("with rewrites role 3 as 0", stored_of(3 * 32 + 9), 4, 1, True, pack([9, 4], [3, 1]))
    for name, stored, want in (("1.x pair is paired", -2 - 12126, True), ("unpaired -1 isn't", -1, False),
                               ("member is paired", s, True), ("empty new value isn't", pack([], [], True), False)):
        one(name, "IsPaired", {"Stored": str(stored)}, b(want))
    one("emptied is -1", "Emptied", {"Stored": str(s)}, "-1")
    one("emptied drops unused bits", "Emptied", {"Stored": str(with_unused(s))}, "-1")
    one("emptied keeps paused", "Emptied", {"Stored": str(pack([3], [1], True))}, str(pack([], [], True)))
    one("job key", "JobKey", {"Id": "12207", "Res": "flax"}, "12207|flax")
    one("park key", "ParkKey", {"Id": "12207", "Res": "flax"}, "12207|flax|park")
    return cases


# --- reference model of BPL_FDDispatch's scoring and minimum load
TAU = 600.0


def good_value(units, age):
    return units * (1.0 + age / TAU)


def meets_minimum(units, share, hold, want_total, oldest, max_wait):
    if units <= 0:
        return False
    if oldest >= max_wait:
        return True
    return units >= share * min(hold, want_total) - 0.001


def dispatch_cases():
    cases = []
    for units, age in ((30, 0.0), (30, 600.0), (10, 300.0), (0, 1000.0)):
        cases.append({"name": f"good value {units} aged {age}", "call": "GoodValue",
                      "args": {"Units": str(units), "Age": str(age)},
                      "expect": {"return": f"{good_value(units, age):.6f}"}})
    for name, args in (("no minimum", (5, 0.0, 89, 300, 0.0, 120.0)),
                       ("quarter met", (23, 0.25, 89, 300, 0.0, 120.0)),
                       ("quarter missed", (22, 0.25, 89, 300, 0.0, 120.0)),
                       ("small request served in full", (10, 0.9, 89, 10, 0.0, 120.0)),
                       ("small request partly", (9, 0.9, 89, 10, 0.0, 120.0)),
                       ("waived after waiting", (3, 0.9, 89, 300, 120.0, 120.0)),
                       ("nothing to carry", (0, 0.0, 89, 300, 500.0, 120.0))):
        u, sh, h, w, o, mw = args
        cases.append({"name": f"minimum: {name}", "call": "MeetsMinimum",
                      "args": {"Units": str(u), "Share": str(sh), "Hold": str(h), "WantTotal": str(w),
                               "OldestAge": str(o), "MaxWait": str(mw)},
                      "expect": {"return": b(meets_minimum(u, sh, h, w, o, mw))}})
    cases.append({"name": "good of a key", "call": "GoodOf", "args": {"Key": "12207|flax"}, "expect": {"return": "flax"}})
    return cases


SUITES = {"BPL_FDNet": ("/Game/Mods/FreightDock/Loom/BPL_FDNet", net_cases),
          "BPL_FDDispatch": ("/Game/Mods/FreightDock/Loom/BPL_FDDispatch", dispatch_cases)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = True
    for name, (bp, make) in SUITES.items():
        test = OUT / f"{name}.json"
        report = OUT / f"{name}.report.json"
        report.unlink(missing_ok=True)
        test.write_text(json.dumps({"blueprint": bp, "cases": make()}, indent=1), encoding="utf-8")
        subprocess.run([str(EDITOR), str(PROJECT), "-run=LoomTest", f"-test={test}", f"-report={report}",
                        "-unattended", "-nullrhi", "-nosplash", "-nopause"], capture_output=True)
        if not report.exists():
            print(f"{name}: no report (did the commandlet run?)")
            ok = False
            continue
        r = json.loads(report.read_text(encoding="utf-8"))
        if "error" in r:
            print(f"{name}: {r['error']}")
            ok = False
        cases = r.get("cases", [])
        failed = [c for c in cases if not c.get("ok")]
        for c in failed:
            print(f"FAIL {c.get('name')}: {c.get('error', '')} got {c.get('got')}")
        print(f"{name}: {len(cases) - len(failed)}/{len(cases)} passed")
        ok &= not failed and r.get("ok", False)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
