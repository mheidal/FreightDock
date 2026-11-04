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
FORMAT, FULL, SLOTS = 1 << 30, 1 << 28, 4


def pack(nets, roles, full=False):
    packed = FORMAT + (FULL if full else 0)
    slot = 0
    for net, role in zip(nets, roles):
        if slot < SLOTS and 1 <= net <= 31 and 1 <= role <= 3:
            packed += (role * 32 + net) << (7 * slot)
            slot += 1
    return -packed - 2


def unpack(stored):
    packed = -stored - 2 if stored <= -2 else -1
    is_new = packed >= 0 and bool(packed & FORMAT)
    nets, roles = [], []
    for i in range(SLOTS):
        m = (packed >> (7 * i)) & 127 if is_new else 0
        net, role = m % 32, m // 32
        if net == 0 or role == 0:
            net = role = 0
        nets.append(net)
        roles.append(role)
    full = is_new and bool(packed & FULL)
    old = packed if packed >= 0 and not is_new else -1
    return nets, roles, full, is_new, old


def arr(xs):
    return "(" + ",".join(str(x) for x in xs) + ")"


def b(x):
    return "True" if x else "False"


def net_cases():
    cases = []

    def pack_case(name, nets, roles, full=False):
        cases.append({"name": name, "call": "Pack",
                      "args": {"Nets": arr(nets), "Roles": arr(roles), "Full": b(full)},
                      "expect": {"return": str(pack(nets, roles, full))}})

    def unpack_case(name, stored):
        nets, roles, full, is_new, old = unpack(stored)
        cases.append({"name": name, "call": "Unpack", "args": {"Stored": str(stored)},
                      "expect": {"Nets": arr(nets), "Roles": arr(roles), "Full": b(full),
                                 "IsNew": b(is_new), "OldPartner": str(old)}})

    pack_case("pack one", [1], [3])
    pack_case("pack four", [3, 7, 31, 12], [1, 2, 3, 1])
    pack_case("pack full flag", [5], [2], True)
    pack_case("pack none", [], [])
    pack_case("pack skips bad entries", [0, 32, 4, 9], [1, 1, 0, 2])
    pack_case("pack drops a fifth", [1, 2, 3, 4, 5], [1, 1, 1, 1, 1])
    pack_case("pack maximum", [31, 31, 31, 31], [3, 3, 3, 3], True)

    unpack_case("unpack unpaired -1", -1)
    unpack_case("unpack zero", 0)
    unpack_case("unpack 1.x pair", -2 - 12126)
    unpack_case("unpack 1.x pair to dock 0", -2)
    for nets, roles, full in ([[1], [3], False], [[3, 7, 31, 12], [1, 2, 3, 1], False],
                              [[5], [2], True], [[], [], False], [[31] * 4, [3] * 4, True]):
        unpack_case(f"unpack {nets} {roles} {full}", pack(nets, roles, full))

    s = pack([3, 7], [1, 2])
    cases += [
        {"name": "role on member", "call": "RoleOn", "args": {"Stored": str(s), "Net": "7"}, "expect": {"return": "2"}},
        {"name": "role on non-member", "call": "RoleOn", "args": {"Stored": str(s), "Net": "4"}, "expect": {"return": "0"}},
        {"name": "role on net 0", "call": "RoleOn", "args": {"Stored": str(s), "Net": "0"}, "expect": {"return": "0"}},
        {"name": "provides", "call": "Provides", "args": {"Stored": str(s), "Net": "3"}, "expect": {"return": "True"}},
        {"name": "requester doesn't provide", "call": "Provides", "args": {"Stored": str(s), "Net": "7"}, "expect": {"return": "False"}},
        {"name": "requests", "call": "Requests", "args": {"Stored": str(s), "Net": "7"}, "expect": {"return": "True"}},
        {"name": "both requests", "call": "Requests", "args": {"Stored": str(pack([9], [3])), "Net": "9"}, "expect": {"return": "True"}},
        {"name": "1.x value is no member", "call": "IsMember", "args": {"Stored": str(-2 - 12126)}, "expect": {"return": "False"}},
        {"name": "member", "call": "IsMember", "args": {"Stored": str(s)}, "expect": {"return": "True"}},
        {"name": "empty new value is no member", "call": "IsMember", "args": {"Stored": str(pack([], []))}, "expect": {"return": "False"}},
    ]

    def with_case(name, stored, net, role, ok, result):
        cases.append({"name": name, "call": "With", "args": {"Stored": str(stored), "Net": str(net), "Role": str(role)},
                      "expect": {"Ok": b(ok), "return": str(result)}})

    with_case("with adds", s, 9, 3, True, pack([3, 7, 9], [1, 2, 3]))
    with_case("with changes a role", s, 7, 3, True, pack([3, 7], [1, 3]))
    with_case("with removes", s, 3, 0, True, pack([7], [2]))
    with_case("with removes a non-member", s, 4, 0, True, s)
    four = pack([1, 2, 3, 4], [1, 1, 1, 1])
    with_case("with refuses a fifth", four, 5, 1, False, four)
    with_case("with refuses net 32", s, 32, 1, False, s)
    with_case("with refuses role 4", s, 3, 4, False, s)
    with_case("with replaces a 1.x pair", -2 - 12126, 2, 3, True, pack([2], [3]))
    with_case("with keeps the full flag", pack([3], [1], True), 4, 2, True, pack([3, 4], [1, 2], True))
    for name, stored, want in (("1.x pair is paired", -2 - 12126, True), ("unpaired -1 isn't", -1, False),
                               ("member is paired", s, True), ("empty new value isn't", pack([], [], True), False)):
        cases.append({"name": name, "call": "IsPaired", "args": {"Stored": str(stored)}, "expect": {"return": b(want)}})
    cases.append({"name": "emptied is -1", "call": "Emptied", "args": {"Stored": str(s)}, "expect": {"return": "-1"}})
    cases.append({"name": "emptied keeps full", "call": "Emptied", "args": {"Stored": str(pack([3], [1], True))},
                  "expect": {"return": str(pack([], [], True))}})
    cases.append({"name": "with full", "call": "WithFull", "args": {"Stored": str(s), "Full": "True"},
                  "expect": {"return": str(pack([3, 7], [1, 2], True))}})
    return cases


SUITES = {"BPL_FDNet": ("/Game/Mods/FreightDock/Loom/BPL_FDNet", net_cases)}


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
