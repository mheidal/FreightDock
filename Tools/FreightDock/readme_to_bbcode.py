"""Convert the repo's README.md to Steam BBCode, for the Workshop item's description.

    uv run python readme_to_bbcode.py [README] [-o OUT]

Markdown is parsed with mistune and rendered as Steam's tags: [h1]-[h3], [b], [i], [strike], [url=...],
[img], [list]/[olist] with [*], [code], [quote] and [hr]. Inline code becomes plain text, since Steam's [code] is a
block. Soft line breaks become spaces, as GitHub shows them. The description is pasted into the item's page by hand:
uploads keep the page's description (see Docs/FreightDock/Publish to Workshop.md).
"""
import argparse
from pathlib import Path

import mistune

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "README.md"
DEFAULT_OUT = ROOT / "Saved" / "Workshop" / "FreightDock" / "description.txt"


class SteamRenderer(mistune.HTMLRenderer):
    """Steam BBCode instead of HTML; text is passed through unescaped."""

    def text(self, text):
        return text

    def emphasis(self, text):
        return f"[i]{text}[/i]"

    def strong(self, text):
        return f"[b]{text}[/b]"

    def strikethrough(self, text):
        return f"[strike]{text}[/strike]"

    def link(self, text, url, title=None):
        return f"[url={url}]{text}[/url]"

    def image(self, text, url, title=None):
        return f"[img]{url}[/img]"

    def codespan(self, text):
        return text

    def linebreak(self):
        return "\n"

    def softbreak(self):
        return " "

    def inline_html(self, html):
        return html

    def paragraph(self, text):
        return text.strip() + "\n\n"

    def heading(self, text, level, **attrs):
        tag = f"h{min(level, 3)}"
        return f"[{tag}]{text}[/{tag}]\n"

    def blank_line(self):
        return ""

    def thematic_break(self):
        return "[hr][/hr]\n"

    def block_text(self, text):
        return text

    def block_code(self, code, info=None):
        return f"[code]{code.rstrip()}[/code]\n\n"

    def block_quote(self, text):
        return f"[quote]{text.strip()}[/quote]\n\n"

    def block_html(self, html):
        return html

    def block_error(self, text):
        return text

    def list(self, text, ordered, **attrs):
        tag = "olist" if ordered else "list"
        return f"[{tag}]\n{text}[/{tag}]\n\n"

    def list_item(self, text):
        return f"[*]{text.strip()}\n"


def convert(markdown_text):
    md = mistune.create_markdown(renderer=SteamRenderer(), plugins=["strikethrough"])
    return md(markdown_text).strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("readme", nargs="?", type=Path, default=DEFAULT_IN)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out = convert(args.readme.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out, encoding="utf-8")
    print(f"Wrote {args.out} ({len(out)} characters)")


if __name__ == "__main__":
    main()
