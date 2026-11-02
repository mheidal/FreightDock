"""Make generated T3D comparable across runs: GUIDs come from one process-wide counter, so the same graph gets
different GUIDs depending on what was generated before it. Renumber them in order of first appearance."""
import re

_GUID = re.compile(r"\b[0-9A-F]{32}\b")


def normalize_t3d(text):
    seen = {}
    return _GUID.sub(lambda m: seen.setdefault(m.group(0), f"{len(seen) + 1:032X}"), text)
