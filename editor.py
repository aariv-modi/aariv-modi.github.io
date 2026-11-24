"""Write, preview and publish essays in your browser.

    python editor.py

Opens http://localhost:8000/edit. Only reachable from this computer.
"""
import html
import os
import re
import subprocess
import sys
import webbrowser
from datetime import date
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import build

PORT = 8000
SITE_URL = "https://aariv-modi.github.io"
ALLOWED_ORIGINS = {f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"}

STYLE = """<style>
form { display: grid; gap: 1em; }
label { display: grid; gap: 0.25em; font-weight: 600; }
input, textarea, button {
  font: inherit; font-weight: normal; color: inherit; background: var(--bg);
  border: 1px solid var(--rule); border-radius: 3px; padding: 0.4em 0.6em;
}
textarea { min-height: 60vh; line-height: 1.6; resize: vertical; }
button { cursor: pointer; }
.row { display: flex; gap: 0.6em; flex-wrap: wrap; align-items: center; }
.message { padding: 0.6em 0.8em; border: 1px solid var(--rule); }
.message.error { border-color: #c33; }
.muted { color: var(--muted); }
details pre { white-space: pre-wrap; font-size: 0.8em; }
</style>"""

HELP = (
    "Leave a blank line between paragraphs. "
    "<code>*italic*</code>, <code>**bold**</code>, <code>[link](https://...)</code>, "
    "<code>## Heading</code>, <code>- list item</code>, <code>&gt; quote</code>. "
    "For notes, write <code>[1]</code> in the text and add a <code>## Notes</code> heading at the end "
    "with a paragraph starting <code>[1]</code>."
)


# ---- Essay files ------------------------------------------------------------

def clean_slug(text):
    return text if re.fullmatch(r"[a-z0-9][a-z0-9-]*", text or "") else ""


def essay_path(slug):
    return build.ESSAYS / f"{slug}.md"


def new_slug(title):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].strip("-") or "untitled"
    if base == "index":
        base = "index-essay"
    slug, n = base, 2
    while essay_path(slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def write_essay(slug, title, when, body, draft):
    head = f"title: {title}\ndate: {when}\n" + ("draft: yes\n" if draft else "")
    essay_path(slug).write_text(head + "\n" + body.strip() + "\n", encoding="utf-8")


def all_essays():
    rows = []
    for path in build.ESSAYS.glob("*.md"):
        try:
            meta, _ = build.read_source(path)
        except build.BuildError:
            meta = {"title": path.name, "date": "", "draft": True}
        rows.append((meta.get("date", ""), path.stem, meta.get("title") or path.stem, meta["draft"]))
    return sorted(rows, reverse=True)


# ---- Publishing (git) -------------------------------------------------------

def git(*args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", *args], cwd=build.ROOT, env=env, capture_output=True, text=True, timeout=120
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def push_essay(slug, message):
    """Commit this one essay file and push. Returns (ok, log)."""
    path = f"essays/{slug}.md"
    log = []
    code, out = git("add", "--", path)
    if code:
        return False, out
    changed, _ = git("diff", "--cached", "--quiet", "--", path)
    if changed:
        code, out = git("commit", "-m", message, "--", path)
        log.append(out)
        if code:
            return False, "\n".join(log)
    code, out = git("push")
    log.append(out)
    return code == 0, "\n".join(x for x in log if x)


# ---- Pages ------------------------------------------------------------------

def editor_page(slug="", title="", when="", body="", draft=True, message="", log="", error=False):
    esc = html.escape
    parts = [STYLE]
    if slug:
        status = "Draft (only on this computer)" if draft else "Published"
        parts.append(f'<p class="row"><a href="/edit">+ New essay</a> <span class="muted">{status}</span></p>')
    else:
        parts.append("<h1>New essay</h1>")
    if message:
        details = f"<details><summary>Details</summary><pre>{esc(log)}</pre></details>" if log else ""
        parts.append(f'<div class="message{" error" if error else ""}">{message}{details}</div>')

    buttons = ['<button name="action" value="save">Save</button>']
    buttons.append('<button name="action" value="publish">Publish</button>' if draft else
                   '<button name="action" value="publish">Publish changes</button>'
                   '<button name="action" value="unpublish">Unpublish</button>')
    if slug:
        buttons.append(f'<a href="/{slug}.html" target="_blank">Preview</a>')

    parts.append(f"""<form method="post" action="/save">
<input type="hidden" name="slug" value="{esc(slug)}">
<label>Title <input name="title" value="{esc(title)}" required autofocus></label>
<label>Date <input name="date" value="{esc(when or date.today().isoformat())}" required></label>
<label>Essay <textarea name="body">{esc(body)}</textarea></label>
<div class="row">{''.join(buttons)}</div>
</form>
<p class="muted">{HELP}</p>""")

    rows = all_essays()
    if rows:
        items = "\n".join(
            f'<li><a href="/edit?slug={s}">{esc(t)}</a>{" <span class=muted>(draft)</span>" if d else ""}</li>'
            for _, s, t, d in rows
        )
        parts.append(f'<h2>Your essays</h2>\n<ul class="essays">\n{items}\n</ul>')
    return "\n".join(parts)


def open_essay(slug):
    if not slug or not essay_path(slug).exists():
        return editor_page()
    try:
        meta, body = build.read_source(essay_path(slug))
    except build.BuildError as err:
        return editor_page(message=html.escape(str(err)), error=True)
    return editor_page(slug, meta.get("title", ""), meta.get("date", ""), body.strip(), meta["draft"])


def save(form):
    action = form.get("action", "save")
    title = " ".join(form.get("title", "").split())
    when = form.get("date", "").strip()
    body = form.get("body", "").replace("\r\n", "\n")
    slug = clean_slug(form.get("slug", ""))
    existing = bool(slug) and essay_path(slug).exists()
    was_draft = build.read_source(essay_path(slug))[0]["draft"] if existing else True

    def problem(text):
        return editor_page(slug if existing else "", title, when, body, was_draft, text, error=True)

    if not title:
        return problem("The essay needs a title.")
    if not build.parse_date(when):
        return problem("The date should look like 2026-11-24 (or 2026-11).")

    if not existing:
        slug = new_slug(title)
    draft = {"publish": False, "unpublish": True}.get(action, was_draft)
    write_essay(slug, title, when, body, draft)

    try:
        build.load(essay_path(slug))
    except build.BuildError as err:
        return editor_page(slug, title, when, body, draft, f"Saved, but: {html.escape(str(err))}", error=True)

    if action == "save":
        where = "on this computer" if draft else "on this computer; click Publish changes to put this version online"
        return editor_page(slug, title, when, body, draft, f"Saved {where}.")

    verb = "Publish" if action == "publish" else "Unpublish"
    ok, log = push_essay(slug, f"{verb}: {title}")
    if not ok:
        return editor_page(slug, title, when, body, draft,
                           "Saved on this computer, but sending it to GitHub failed.", log, error=True)
    url = f"{SITE_URL}/{slug}.html"
    if action == "publish":
        text = f'Published. It will be live in a minute or two at <a href="{url}" target="_blank">{url}</a>.'
    else:
        text = "Unpublished. It will disappear from the site in a minute or two."
    return editor_page(slug, title, when, body, draft, text, log)


# ---- Server -----------------------------------------------------------------

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(build.OUT), **kwargs)

    def send_page(self, content, title="Editor"):
        data = build.page(title, content).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/edit", "/edit/"):
            slug = clean_slug(parse_qs(url.query).get("slug", [""])[0])
            return self.send_page(open_essay(slug))
        if url.path.endswith((".html", "/")):
            try:
                build.build(include_drafts=True)
            except build.BuildError as err:
                return self.send_error(500, str(err))
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/save":
            return self.send_error(404)
        if self.headers.get("Origin") not in ALLOWED_ORIGINS:  # blocks other websites from posting here
            return self.send_error(403)
        length = int(self.headers.get("Content-Length", 0))
        fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        self.send_page(save({k: v[0] for k, v in fields.items()}))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    build.ESSAYS.mkdir(exist_ok=True)
    try:
        build.build(include_drafts=True)
    except build.BuildError as err:
        sys.exit(f"Error: {err}")
    address = f"http://localhost:{PORT}/edit"
    print(f"Editor running at {address}  (keep this window open; Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        webbrowser.open(address)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
