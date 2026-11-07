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
FORMAT, V2, FULL, PAUSED, SLOTS, NORMAL = 1 << 30, 1 << 29, 1 << 28, 1 << 27, 3, 1


def pack(nets, roles, prios=None, full=False, paused=False):
    packed = V2 + (FULL if full else 0) + (PAUSED if paused else 0)
    prios = prios or []
    slot = 0
    for i, (net, role) in enumerate(zip(nets, roles)):
        prio = prios[i] if i < len(prios) and 0 <= prios[i] <= 3 else NORMAL
        if slot < SLOTS and 1 <= net <= 31 and 1 <= role <= 3:
            packed += (prio * 128 + role * 32 + net) << (9 * slot)
            slot += 1
    return -packed - 2


def pack_old(nets, roles, full=False):
    """The old 4 x 7-bit layout (no V2 bit)."""
    packed = FORMAT + (FULL if full else 0)
    for slot, (net, role) in enumerate(zip(nets, roles)):
        packed += (role * 32 + net) << (7 * slot)
    return -packed - 2


def unpack(stored):
    packed = -stored - 2 if stored <= -2 else -1
    v2 = packed >= 0 and not packed & FORMAT and bool(packed & V2)
    is_new = (packed >= 0 and bool(packed & FORMAT)) or v2
    found = []
    if is_new:
        for i in range(SLOTS if v2 else 4):
            if v2:
                m = (packed >> (9 * i)) & 511
                net, role, prio = m % 32, (m // 32) % 4, m // 128
            else:
                m = (packed >> (7 * i)) & 127
                net, role, prio = m % 32, m // 32, NORMAL
            if net and role:
                found.append((net, role, prio))
    found.sort(key=lambda t: t[0])
    found = (found + [(0, 0, NORMAL)] * SLOTS)[:SLOTS]
    nets, roles, prios = [f[0] for f in found], [f[1] for f in found], [f[2] for f in found]
    full = is_new and bool(packed & FULL)
    paused = v2 and bool(packed & PAUSED)
    old = packed if packed >= 0 and not is_new else -1
    return nets, roles, prios, full, paused, is_new, old


def arr(xs):
    return "(" + ",".join(str(x) for x in xs) + ")"


def b(x):
    return "True" if x else "False"


def net_cases():
    cases = []

    def pack_case(name, nets, roles, prios=None, full=False, paused=False):
        cases.append({"name": name, "call": "Pack",
                      "args": {"Nets": arr(nets), "Roles": arr(roles), "Prios": arr(prios or []), "Full": b(full),
                               "Paused": b(paused)},
                      "expect": {"return": str(pack(nets, roles, prios, full, paused))}})

    def unpack_case(name, stored):
        nets, roles, prios, full, paused, is_new, old = unpack(stored)
        cases.append({"name": name, "call": "Unpack", "args": {"Stored": str(stored)},
                      "expect": {"Nets": arr(nets), "Roles": arr(roles), "Prios": arr(prios), "Full": b(full),
                                 "Paused": b(paused), "IsNew": b(is_new), "OldTarget": str(old)}})

    pack_case("pack one", [1], [3])
    pack_case("pack three", [3, 7, 31], [1, 2, 3], [0, 2, 3])
    pack_case("pack full flag", [5], [2], None, True)
    pack_case("pack paused", [5], [2], None, False, True)
    pack_case("pack none", [], [])
    pack_case("pack skips bad entries", [0, 32, 4, 9], [1, 1, 0, 2])
    pack_case("pack drops a fourth", [1, 2, 3, 4], [1, 1, 1, 1])
    pack_case("pack bad priority is normal", [6], [1], [7])
    pack_case("pack maximum", [31, 31, 31], [3, 3, 3], [3, 3, 3], True, True)

    unpack_case("unpack unpaired -1", -1)
    unpack_case("unpack zero", 0)
    unpack_case("unpack 1.x pair", -2 - 12126)
    unpack_case("unpack 1.x pair to dock 0", -2)
    for nets, roles, prios, full, paused in ([[1], [3], None, False, False],
                                             [[3, 7, 31], [1, 2, 3], [0, 2, 3], False, False],
                                             [[5], [2], None, True, False], [[], [], None, False, True],
                                             [[31] * 3, [3] * 3, [3] * 3, True, True],
                                             [[9, 2], [1, 2], [2, 0], False, False]):
        unpack_case(f"unpack {nets} {roles} {prios} {full} {paused}", pack(nets, roles, prios, full, paused))
    unpack_case("unpack old layout", pack_old([3, 7], [1, 2]))
    unpack_case("unpack old layout keeps the lowest 3", pack_old([12, 3, 31, 7], [1, 2, 3, 1], True))

    s = pack([3, 7], [1, 2], [1, 2])
    old = pack_old([3, 7], [1, 2])

    def one(name, call, args, ret):
        cases.append({"name": name, "call": call, "args": args, "expect": {"return": ret}})

    one("role on member", "RoleOn", {"Stored": str(s), "Net": "7"}, "2")
    one("role on non-member", "RoleOn", {"Stored": str(s), "Net": "4"}, "0")
    one("role on net 0", "RoleOn", {"Stored": str(s), "Net": "0"}, "0")
    one("role on old layout", "RoleOn", {"Stored": str(old), "Net": "7"}, "2")
    one("provides", "Provides", {"Stored": str(s), "Net": "3"}, "True")
    one("requester doesn't provide", "Provides", {"Stored": str(s), "Net": "7"}, "False")
    one("requests", "Requests", {"Stored": str(s), "Net": "7"}, "True")
    one("both requests", "Requests", {"Stored": str(pack([9], [3])), "Net": "9"}, "True")
    one("1.x value is no member", "IsMember", {"Stored": str(-2 - 12126)}, "False")
    one("member", "IsMember", {"Stored": str(s)}, "True")
    one("empty new value is no member", "IsMember", {"Stored": str(pack([], []))}, "False")
    one("priority on member", "PrioOn", {"Stored": str(s), "Net": "7"}, "2")
    one("priority on non-member is normal", "PrioOn", {"Stored": str(s), "Net": "4"}, "1")
    one("with priority", "WithPrio", {"Stored": str(s), "Net": "3", "Prio": "3"}, str(pack([3, 7], [1, 2], [3, 2])))
    one("with priority on non-member", "WithPrio", {"Stored": str(s), "Net": "4", "Prio": "3"}, str(s))
    one("with priority out of range", "WithPrio", {"Stored": str(s), "Net": "3", "Prio": "4"}, str(s))
    one("with paused", "WithPaused", {"Stored": str(s), "Paused": "True"}, str(pack([3, 7], [1, 2], [1, 2], False, True)))
    one("paused", "IsPaused", {"Stored": str(pack([3], [1], None, False, True))}, "True")
    one("not paused", "IsPaused", {"Stored": str(s)}, "False")
    one("pause without networks", "WithPaused", {"Stored": "-1", "Paused": "True"}, str(pack([], [], None, False, True)))

    def with_case(name, stored, net, role, ok, result):
        cases.append({"name": name, "call": "With", "args": {"Stored": str(stored), "Net": str(net), "Role": str(role)},
                      "expect": {"Ok": b(ok), "return": str(result)}})

    with_case("with adds", s, 9, 3, True, pack([3, 7, 9], [1, 2, 3], [1, 2, 1]))
    with_case("with changes a role, keeps priority", s, 7, 3, True, pack([3, 7], [1, 3], [1, 2]))
    with_case("with removes", s, 3, 0, True, pack([7], [2], [2]))
    with_case("with removes a non-member", s, 4, 0, True, s)
    three = pack([1, 2, 3], [1, 1, 1])
    with_case("with refuses a fourth", three, 5, 1, False, three)
    with_case("with refuses net 32", s, 32, 1, False, s)
    with_case("with refuses role 4", s, 3, 4, False, s)
    with_case("with replaces a 1.x pair", -2 - 12126, 2, 3, True, pack([2], [3]))
    with_case("with keeps the flags", pack([3], [1], None, True, True), 4, 2, True, pack([3, 4], [1, 2], None, True, True))
    with_case("with converts the old layout", pack_old([12, 3, 31, 7], [1, 2, 3, 1]), 12, 0, True, pack([3, 7], [2, 1]))
    for name, stored, want in (("1.x pair is paired", -2 - 12126, True), ("unpaired -1 isn't", -1, False),
                               ("member is paired", s, True), ("empty new value isn't", pack([], [], None, True), False)):
        one(name, "IsPaired", {"Stored": str(stored)}, b(want))
    one("emptied is -1", "Emptied", {"Stored": str(s)}, "-1")
    one("emptied keeps full", "Emptied", {"Stored": str(pack([3], [1], None, True))}, str(pack([], [], None, True)))
    one("emptied keeps paused", "Emptied", {"Stored": str(pack([3], [1], None, False, True))},
        str(pack([], [], None, False, True)))
    one("job key", "JobKey", {"Id": "12207", "Res": "flax"}, "12207|flax")
    one("park key", "ParkKey", {"Id": "12207", "Res": "flax"}, "12207|flax|park")
    one("with full", "WithFull", {"Stored": str(s), "Full": "True"}, str(pack([3, 7], [1, 2], [1, 2], True)))
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
