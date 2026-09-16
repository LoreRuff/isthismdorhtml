# Sample document

This `.md` file demonstrates what the viewer does: you write Markdown, the
server converts it to HTML on the fly. Everything below is server-side
rendering, no client-side JS beyond auto-refresh.

## Obsidian wikilinks

`[[double bracket]]` links resolve by the `.md` file's name, wherever it sits
in the tree, with Obsidian semantics: [[sample-document|Sample document]]
points to this very file. An unresolved name stays an honest link that
answers 404, e.g. [[DoesNotExist]].

Aliases supported: [[sample-document|aliased link]].

## Formatting

**Bold**, *italic*, `inline code`, and a list:

- first item
- second item
  - nested

## Table

| Column A | Column B |
|----------|----------|
| cell 1   | cell 2   |
| cell 3   | cell 4   |

## Code block

```python
def greet(name: str) -> str:
    # Syntax highlighting comes from Pygments (monokai theme)
    return f"Hello, {name}!"
```

## Blockquote

> Blockquotes render with the dark theme's sidebar bar.

---

Add, edit or remove files under `toview/` while the server runs: the homepage
refreshes on every request and wikilinks to brand-new notes resolve
immediately, no restart needed.
