"""Build the essay site.

    python build.py          build the site into the site/ folder
    python build.py serve    preview at http://localhost:8000 (rebuilds on every refresh)
"""
import html
import re
import shutil
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from string import Template

# ---- Settings: edit these -------------------------------------------------

SITE_TITLE = "Aariv"
SITE_URL = "https://aariv-modi.github.io"  # the site's address (used by the RSS feed)
INTRO = ""                        # optional sentence shown above the list of essays

# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
ESSAYS = ROOT / "essays"
FILES = ROOT / "files"   # images and other files, copied to site/files
OUT = ROOT / "site"


class BuildError(Exception):
    pass


# ---- Markdown (the small subset essays need) ------------------------------

def inline(text):
    text = html.escape(text)
    codes = []

    def stash(m):
        codes.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(?!\s)(.+?)(?<!\s)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[(\d+)\]", r'<a class="ref" id="ref\1" href="#note\1">[\1]</a>', text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def list_html(tag, lines, marker):
    items = []
    for line in lines:
        m = re.match(marker, line)
        if m:
            items.append(line[m.end():].strip())
        elif items:
            items[-1] += " " + line.strip()
    lis = "\n".join(f"<li>{inline(i)}</li>" for i in items)
    return f"<{tag}>\n{lis}\n</{tag}>"


def markdown(text):
    fences = []

    def stash_fence(m):
        fences.append(f"<pre><code>{html.escape(m.group(1))}</code></pre>")
        return f"\n\n\x01{len(fences) - 1}\x01\n\n"

    text = re.sub(r"^```[^\n]*\n(.*?)^```[ \t]*$", stash_fence, text, flags=re.M | re.S)
    text = re.sub(r"^(#{1,6} .*)$", r"\n\1\n", text, flags=re.M)  # headings are always their own block

    out, in_notes = [], False
    for block in re.split(r"\n[ \t]*\n", text.strip()):
        block = block.strip("\n")
        if not block.strip():
            continue
        lines = block.splitlines()
        first = lines[0]

        if re.fullmatch(r"\x01\d+\x01", block.strip()):
            out.append(fences[int(block.strip()[1:-1])])
        elif re.match(r"#{1,6} ", first):
            level = len(first) - len(first.lstrip("#"))
            title = first.lstrip("#").strip()
            in_notes = title.lower() == "notes"
            out.append(f"<h{level}>{inline(title)}</h{level}>")
        elif block.strip() in ("---", "***"):
            out.append("<hr>")
        elif first.startswith("<"):
            out.append(block)  # raw HTML passes through untouched
        elif all(line.startswith(">") for line in lines):
            quote = " ".join(line[1:].strip() for line in lines)
            out.append(f"<blockquote><p>{inline(quote)}</p></blockquote>")
        elif re.match(r"[-*] ", first):
            out.append(list_html("ul", lines, r"[-*] "))
        elif re.match(r"\d+\. ", first):
            out.append(list_html("ol", lines, r"\d+\. "))
        else:
            para = " ".join(line.strip() for line in lines)
            note = re.match(r"\[(\d+)\]\s*(.*)", para) if in_notes else None
            if note:
                n, rest = note.groups()
                out.append(f'<p id="note{n}"><a class="ref" href="#ref{n}">[{n}]</a> {inline(rest)}</p>')
            else:
                out.append(f"<p>{inline(para)}</p>")
    return "\n\n".join(out)


# ---- Essays ----------------------------------------------------------------

def load(path):
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").lstrip()
    head, _, body = raw.partition("\n\n")
    meta = {}
    for line in head.splitlines():
        if ":" not in line:
            raise BuildError(f"{path.name}: the title and date lines must be followed by a blank line")
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip()

    if not meta.get("title"):
        raise BuildError(f"{path.name}: needs a 'title: ...' line at the top")
    if path.stem == "index":
        raise BuildError(f"{path.name}: 'index' is reserved for the home page; rename the file")
    date = meta.get("date", "")
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            when = datetime.strptime(date, fmt)
            break
        except ValueError:
            pass
    else:
        raise BuildError(f"{path.name}: date should look like 2026-11 or 2026-11-24")

    return {
        "slug": path.stem,
        "title": meta["title"],
        "when": when,
        "draft": meta.get("draft", "").lower() in ("yes", "true"),
        "body": markdown(body),
    }


def page(layout, title, content):
    return layout.substitute(
        page_title=html.escape(title),
        site_title=html.escape(SITE_TITLE),
        content=content,
    )


def build():
    layout = Template((ROOT / "layout.html").read_text(encoding="utf-8"))
    essays = [load(p) for p in sorted(ESSAYS.glob("*.md"))]
    essays.sort(key=lambda e: e["when"], reverse=True)
    published = [e for e in essays if not e["draft"]]

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy(ROOT / "style.css", OUT)
    if FILES.exists():
        shutil.copytree(FILES, OUT / "files")

    for e in published:
        content = (
            f"<article>\n<h1>{html.escape(e['title'])}</h1>\n"
            f"<p class=\"date\">{e['when']:%B %Y}</p>\n\n{e['body']}\n</article>"
        )
        (OUT / f"{e['slug']}.html").write_text(page(layout, e["title"], content), encoding="utf-8")

    intro = f"<p>{inline(INTRO)}</p>\n" if INTRO else ""
    items = "\n".join(f'<li><a href="{e["slug"]}.html">{html.escape(e["title"])}</a></li>' for e in published)
    listing = f'<ul class="essays">\n{items}\n</ul>' if published else "<p>No essays yet.</p>"
    index = f'{intro}{listing}\n<footer><a href="feed.xml">RSS</a></footer>'
    (OUT / "index.html").write_text(page(layout, SITE_TITLE, index), encoding="utf-8")

    (OUT / "feed.xml").write_text(feed(published), encoding="utf-8")
    return len(published), len(essays) - len(published)


def feed(essays):
    base = SITE_URL.rstrip("/")
    esc = html.escape
    items = "".join(
        f"""
<item>
<title>{esc(e['title'])}</title>
<link>{base}/{e['slug']}.html</link>
<guid>{base}/{e['slug']}.html</guid>
<pubDate>{format_datetime(e['when'].replace(tzinfo=timezone.utc))}</pubDate>
<description>{esc(e['body'])}</description>
</item>"""
        for e in essays
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
<title>{esc(SITE_TITLE)}</title>
<link>{base}/</link>
<description>Essays by {esc(SITE_TITLE)}</description>{items}
</channel>
</rss>
"""


# ---- Preview server ---------------------------------------------------------

def serve(port=8000):
    import http.server

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(OUT), **kwargs)

        def do_GET(self):
            if self.path.split("?")[0].endswith((".html", "/")):
                try:
                    build()
                except BuildError as err:
                    self.send_error(500, str(err))
                    return
            super().do_GET()

        def log_message(self, *args):
            pass

    print(f"Preview at http://localhost:{port}  (edit an essay, then refresh; Ctrl+C to stop)")
    http.server.HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    try:
        built, drafts = build()
    except BuildError as err:
        sys.exit(f"Error: {err}")
    print(f"Built {built} essay(s) into {OUT}" + (f", skipped {drafts} draft(s)" if drafts else ""))
    if sys.argv[1:] == ["serve"]:
        serve()
