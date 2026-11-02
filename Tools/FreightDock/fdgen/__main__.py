"""Command line.

    python -m fdgen <FunctionName>                 T3D for one function on stdout
    python -m fdgen --emit <out_dir> <Name> ...    NN_<Name>.t3d + NN_<Name>.json (ImportFunction spec), in order
    python -m fdgen --list                         every function, its module, and whether it has an install spec
"""
import json
import os
import sys

from fdgen.registry import GRAPHS, OWNER, SPECS


def emit(out_dir, names):
    """Write NN_<name>.t3d and NN_<name>.json (the ImportFunction spec) for each function, in order."""
    os.makedirs(out_dir, exist_ok=True)
    for i, name in enumerate(names, 1):
        if name not in SPECS:
            raise SystemExit(f"{name}: no install spec in SPECS")
        base = f"{i:02d}_{name}"
        with open(os.path.join(out_dir, base + ".t3d"), "w", encoding="utf-8") as f:
            f.write(GRAPHS[name]())
        spec = dict(function=name, t3d=base + ".t3d", **SPECS[name])
        with open(os.path.join(out_dir, base + ".json"), "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=1)
        print(os.path.join(out_dir, base + ".json"))


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    if argv[0] == "--emit":
        emit(argv[1], argv[2:])
    elif argv[0] == "--list":
        for name in sorted(GRAPHS):
            print(f"{name:24} {OWNER[name]:26} {'spec' if name in SPECS else '-'}")
    else:
        sys.stdout.write(GRAPHS[argv[0]]())


if __name__ == "__main__":
    main(sys.argv[1:])
