# isthismdorhtml

> A single-file Flask viewer for folders of `.md` and `.html` files: navigate
> subdirectories, read Markdown rendered on the fly, read HTML served byte-for-byte.
> One process, one port, one Python file.

Born as a read-only expounder for an Obsidian vault (recipes), then generalized
into an agnostic document viewer: Markdown gets converted, HTML is already a
finished document and is rendered faithfully as-is.

## Features

- **Agnostic viewer** — `.md` files are converted to HTML server-side;
  `.html`/`.htm` files are served raw, byte-for-byte, with no template wrapping
- **Recursive navigation** — the homepage lists every document in `MD_ROOT`
  grouped by subfolder, sorted; hidden dirs (`.*`) and `__pycache__` skipped
- **Obsidian wikilinks** — `[[Note]]` and `[[Note|alias]]` resolve by basename
  anywhere in the tree (Obsidian semantics), ambiguous names → first alphabetically;
  the index is rebuilt per request, so notes added or removed at runtime resolve
  immediately without a restart
- **Rich Markdown** — fenced code with Pygments highlighting (monokai), tables,
  TOC, definition lists, attribute lists
- **Dark theme** built in; no client-side JS beyond a tiny auto-refresh
  (reloads a Markdown page only when the file's mtime actually changed)
- **Path-traversal hard** — `realpath` on both root and request: any `../` or
  symlink escaping the root is a plain 404, never a read outside `MD_ROOT`
- **Sanitized output** — filesystem-derived names are HTML-escaped and the
  rendered Markdown is sanitized (nh3) before it reaches the browser
- **No build step** — a single Python file, four dependencies

## Run

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
MD_ROOT=toview MD_TITLE="My Docs" PORT=5000 .venv/bin/python server.py
```

Open `http://localhost:5000`.

| Env var   | Default            | Meaning                                  |
|-----------|--------------------|------------------------------------------|
| `MD_ROOT` | `toview`           | document root (relative or absolute)     |
| `MD_TITLE`| `Document Viewer`  | site title                               |
| `PORT`    | `5000`             | HTTP port                                |
| `VIEWER_HOST` | `0.0.0.0`       | bind interface (`127.0.0.1` = only this machine) |

Note: the env variable is `VIEWER_HOST`, not `HOST` — `HOST` is a standard
shell variable (the hostname) and would silently override the bind.

### Configuration file

Settings can live in `viewer.conf` (INI format, next to `server.py`, path
overridable with `VIEWER_CONFIG`) so a permanent installation needs no flags:

```ini
[viewer]
title = My Recipe Book
root = toview
port = 5000
host = 0.0.0.0
```

Precedence: environment variables override the config file, which overrides
the built-in defaults.

### Changing the port

Pass any free port via `PORT` (the server listens on all interfaces):

```bash
PORT=8080 MD_ROOT=toview .venv/bin/python server.py   # → http://localhost:8080
```

### Accessing from other devices (firewall)

By default the server binds to `0.0.0.0` (all interfaces); restrict it to the
local machine with `VIEWER_HOST=127.0.0.1`. Most firewalls block inbound connections
by default — open the chosen port once, e.g. for port 5000:

```bash
# firewalld (openSUSE, RHEL, Fedora)
sudo firewall-cmd --add-port=5000/tcp --permanent && sudo firewall-cmd --reload

# ufw (Debian/Ubuntu)
sudo ufw allow 5000/tcp
```

Then reach the viewer from any device on the LAN at
`http://<server-ip>:5000`. Only open the port if you trust the network:
the viewer serves every document under `MD_ROOT` unauthenticated.

## File types

| Extension      | Served as                                     |
|----------------|-----------------------------------------------|
| `.md`          | rendered HTML (converted server-side)          |
| `.html` / `.htm` | raw bytes, `text/html`, untouched            |

## Stack

| Layer    | Choice |
|----------|--------|
| Server   | Flask, single file (`server.py`) |
| Markdown | python-markdown + Pygments |
| Frontend | zero JS frameworks; one auto-refresh sniffer |

## Security notes

- Read-only by design: the viewer never writes anything under `MD_ROOT`.
- `realpath` containment on every request; requests resolving outside the root
  return 404.
- Every filename/path/title interpolated in the homepage and document pages is
  HTML-escaped (files come from the filesystem, possibly synced folders).
- Rendered Markdown is sanitized with `nh3` (allowlist-based): raw HTML and
  `attr_list` attributes survive conversion but scripts/event handlers are
  stripped before the browser sees them.
- `.html`/`.htm` files are still served byte-for-byte, untouched: a raw HTML
  document is by definition a finished document, and sanitizing it would change
  its content. Serving your own untrusted files as raw HTML is an accepted
  risk, same nature as opening them in a browser.
- The wikilink index is rebuilt per Markdown conversion (one `os.walk`), so a
  live tree works with no cache to invalidate.

## License

AGPL-3.0 — see [LICENSE](LICENSE).

## Development

Built with strong AI assistance (GLM via opencode), humans leading the ideas,
testing and debugging — declared openly, as it shaped how the project was built.
See [SPEC.md](SPEC.md) for the as-built map.
