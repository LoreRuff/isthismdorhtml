# ISTHISMDORHTML — Build Spec v1.1 (as-built)

> Single-file Flask document viewer: folders of `.md` (converted server-side)
> and `.html` (served raw) browsed recursively, Obsidian wikilinks resolved by
> basename, dark theme, auto-refresh on real change, path-traversal-proof.
> This SPEC describes the code **as it is** — verify against `server.py`
> before extending anything.

---

## 0. Invariants (do not break)

1. **One file.** All logic lives in `server.py`. No blueprint, no package
   layout, no build step. If a change can't stay in one readable file, the
   change is wrong.
2. **Read-only output, live input.** The server never writes under `MD_ROOT`.
   The tree may change under it: document lists and the wikilink index are
   rebuilt per request, so runtime additions/removals need no restart.
3. **Raw is raw.** `.html`/`.htm` files are served byte-for-byte with no
   template, no injection, no wrapper. Faithfulness to the file outranks
   navigation niceties.
4. **Contained.** Every request path is resolved with `os.path.realpath` and
   must stay inside the realpath of `MD_ROOT`. Outside → 404. No exception.
5. **HTML escaping discipline.** All generated markup (homepage, breadcrumb,
   links) must remain safe with hostile filenames; never switch to string
   concatenation of unescaped user content.

## 1. Request map and settings

Settings resolve env var → `viewer.conf` `[viewer]` section → built-in default
(see `_impostazione()`). Keys: `MD_ROOT`/`root`, `MD_TITLE`/`title`,
`PORT`/`port`.

| Route | Behaviour |
|-------|-----------|
| `GET /` | homepage: recursive doc list grouped by subfolder |
| `GET /visualizza/<path>` | `.md` → converted page (template + mtime); `.html`/`.htm` → raw bytes, `text/html`; anything else → 404 |

## 2. Markdown pipeline

- Extensions: `fenced_code`, `tables`, `toc`, `codehilite` (monokai via
  Pygments HtmlFormatter, CSS emitted once at startup), `def_list`, `attr_list`,
  plus the in-file `WikilinkExtension`.
- Wikilink preprocessor: `[[Name]]` / `[[Name|alias]]` → link to
  `/visualizza/<resolved>.md`. Resolution: basename index (lowercased) rebuilt
  once per conversion (`aggiorna_indice_wikilink()`) from a single `os.walk`;
  unknown names link to the root-level attempt and 404 honestly.
- Page body carries `data-mtime` (file mtime as string) — the client reloads
  only when a refetch reports a different value.

## 3. Auto-refresh contract

- The template's JS compares the rendered page's `data-mtime` against a
  refetch of the same URL; reload only on mismatch. Raw HTML pages have no
  template, hence no auto-refresh (by design: raw stays raw).

## 4. Failure modes (as built)

- Missing `MD_ROOT`: homepage fails loud with the culprit path, not a silent
  "no documents".
- `os.walk` on a missing dir is silent; the explicit `NotADirectoryError`
  guard in `elenco_file()` exists precisely to surface that case.
- Dev server warning (`Werkzeug` production notice) is accepted: this is a
  personal, LAN-scope expounder. Do not add a WSGI server dependency without
  cause.

## 5. Extension notes

- New file types: add the extension to `elenco_file()`'s suffix tuple and a
  branch in `visualizza()`; keep the raw/converted split explicit.
- New Markdown extensions: append to `EXTENSIONI`; if they need CSS, extend
  `CSS_PYGMENTS` accordingly.
