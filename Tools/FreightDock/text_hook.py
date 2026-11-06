"""Claude Code PostToolUse hook (Edit|Write): keeps FreightDock's player-facing text in one place and short.

- An edit of Content/Mods/FreightDock/Loom/BPL_FDText.lm (all of the mod's text): lists the entries the edit wrote,
  flagging mechanical signs of wordiness (a final full stop, a leading article, more than one sentence), so each one
  is reviewed for succinctness (short fragments, not sentences).
- An edit of any other FreightDock .lm: flags text written straight into code (SetText, SetLabelText, Toast, Setup,
  widget Text defaults) instead of going through BPL_FDText.T. BPL_FDCheat.lm (dev only) is skipped.

Reads the hook's JSON on stdin; prints a JSON reply with additionalContext only when there is something to say.
"""
import json
import re
import sys

ENTRY = re.compile(r'"((?:freightdock|setting)\.[\w.\-]+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
IN_CODE = re.compile(r'(SetText\(text\(|SetLabelText\(|Toast\(|Setup\(|ToolTipText:\s*|Text:\s*)"((?:[^"\\]|\\.)*)"')
ARTICLE = re.compile(r'^(The|A|An)\s', re.IGNORECASE)


def flags(value):
    out = []
    text = value.replace("\\n", " ")
    if text.rstrip().endswith(".") and not text.rstrip().endswith("..."):
        out.append("ends with a full stop")
    if ARTICLE.match(text):
        out.append("starts with an article")
    if re.search(r"[.!?]\s+\S", text):
        out.append("more than one sentence")
    return out


def written(tool_input):
    """The text the edit put in the file."""
    if "new_string" in tool_input:
        return tool_input.get("new_string") or ""
    if "content" in tool_input:
        return tool_input.get("content") or ""
    return "\n".join(e.get("new_string", "") for e in tool_input.get("edits", []))


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    tool_input = data.get("tool_input") or {}
    path = (tool_input.get("file_path") or "").replace("\\", "/")
    if "/Content/Mods/FreightDock/" not in path or not path.endswith(".lm"):
        return
    name = path.rsplit("/", 1)[-1]
    text = written(tool_input)
    lines = []
    if name == "BPL_FDText.lm":
        for key, value in ENTRY.findall(text):
            f = flags(value)
            lines.append(f'- {key}: "{value}"' + (f"  [{'; '.join(f)}]" if f else ""))
        if lines:
            lines.insert(0, "FreightDock UI text written (BPL_FDText.lm). Review each for succinctness: short "
                            "fragments, not sentences; cut words that add nothing.")
    elif name != "BPL_FDCheat.lm":
        for call, value in IN_CODE.findall(text):
            if re.search(r"[A-Za-z]{2}", value) and not value.startswith(("freightdock.", "setting.")):
                lines.append(f'- {call.strip()} "{value}"')
        if lines:
            lines.insert(0, f"Player-facing text written straight into {name}. Move it to BPL_FDText.lm and look it "
                            "up with BPL_FDText.T (modlog lines can stay):")
    if lines:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": "\n".join(lines)}}))


if __name__ == "__main__":
    main()
