"""Writes a minimal Loom source that shows the per-link memory spike (see "Loom - editor runs out of memory on large
Blueprint builds.md"): one function library, one function, `x += 1` repeated N times (each repeat is a few nodes
and about three links). Build it in the editor, change N (or any line) and save to build it again; the second and
later builds spike. Memory grows with about N squared.

    python loom_link_repro.py <path to Content>/LoomRepro/BPL_LoomLinkRepro.lm [N]
"""
import sys

path = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
body = "\n".join("    x += 1" for _ in range(n))
open(path, "w", encoding="utf-8", newline="\n").write(f"""blueprint BPL_LoomLinkRepro : BlueprintFunctionLibrary at /Game/LoomRepro/BPL_LoomLinkRepro

// {n} additions: a Blueprint with many links in one graph.
pure fn Count(A: int) -> int {{
    let x = A
{body}
    return x
}}
""")
print(f"wrote {path} ({n} additions)")
