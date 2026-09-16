# -*- coding: utf-8 -*-
# Espositore documenti generico (ex ricettario Flask). Un solo file, a scopo leggibile:
# serve una cartella (MD_ROOT) navigando anche le sottocartelle, converte i .md in HTML
# e serve i .html così come sono (agnostico: ogni formato reso al meglio del suo tipo).
#
# Env:
#   MD_ROOT  — radice dei file .md/.html (relativa al cwd o assoluta; default 'toview')
#   MD_TITLE — titolo del sito (default 'Document Viewer')
#   PORT     — porta HTTP (default 5000)
#   VIEWER_HOST — interfaccia di bind (default '0.0.0.0', tutta la rete: il vault
#              è leggibile da chi è sulla stessa rete; '127.0.0.1' per solo locale)
#
# La variabile d'env è VIEWER_HOST, NON HOST: HOST è standard sulle shell unix
# (contiene l'hostname, es. "localhost.localdomain") e schiaccerrebbe il bind.

import configparser
import html
import os
import re
import urllib.parse

import nh3

from flask import Flask, abort
import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from pygments.formatters import HtmlFormatter

app = Flask(__name__)

# Impostazioni: env > viewer.conf > default. L'env serve per girare una volta
# con parametri diversi (test, istanze multiple); il conf è l'installazione
# persistente che non vuole flag a ogni avvio.
CONFIG_PATH = os.environ.get('VIEWER_CONFIG',
                             os.path.join(os.path.dirname(os.path.abspath(__file__)), 'viewer.conf'))
_config = configparser.ConfigParser()
_config.read(CONFIG_PATH)


def _impostazione(env, chiave, default):
    if env in os.environ:
        return os.environ[env]
    try:
        return _config['viewer'][chiave]
    except (KeyError, configparser.Error):
        return default


MD_ROOT = _impostazione('MD_ROOT', 'root', 'toview')
MD_TITLE = _impostazione('MD_TITLE', 'title', 'Document Viewer')
PORT = int(_impostazione('PORT', 'port', '5000'))
HOST = _impostazione('VIEWER_HOST', 'host', '0.0.0.0')

# Radice normalizzata una volta: realpath qui + realpath lato richiesta è la barriera
# anti-path-traversal (un '../' o un symlink fuori radice non passa mai).
RADICE_REALE = os.path.realpath(MD_ROOT)

# Indice basename → percorso relativo: i wikilink Obsidian puntano al NOME della
# nota ovunque stia nel vault, non al suo percorso. Ricostruito a ogni conversione
# .md (v. aggiorna_indice_wikilink): ambigui → primo in ordine alfabetico.
INDICE_WIKILINK: dict[str, str] = {}


def aggiorna_indice_wikilink():
    """Ricostruisce l'indice wikilink prima di ogni conversione .md.

    La radice è viva: note aggiunte o rimosse senza restart devono risolversi
    subito, e il walk di un vault personale costa millisecondi — niente cache
    da invalidare, la costruzione per richiesta è la versione minimale.
    """
    INDICE_WIKILINK.clear()
    if os.path.isdir(RADICE_REALE):
        for dirpath, dirnames, filenames in os.walk(RADICE_REALE):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith('.') and d != '__pycache__')
            for nome in sorted(f for f in filenames if f.endswith('.md') and not f.startswith('.')):
                INDICE_WIKILINK.setdefault(nome[:-3].lower(),
                                           os.path.relpath(os.path.join(dirpath, nome), RADICE_REALE))

# CSS di pygments generato all'avvio con lo schema monokai: coerente col tema scuro
# del template senza incorporare 100 righe di CSS scritti a mano.
CSS_PYGMENTS = HtmlFormatter(style='monokai').get_style_defs('.codehilite')


class WikilinkExtension(Extension):
    """[[Pagina]] e [[Pagina|alias]] → link a /visualizza/Pagina.md.

    Serve a leggere vault Obsidian in sola lettura: i [[wikilink]] sono la
    sintassi nativa lì e senza preprocessor resterebbero testo letterale.
    """

    WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]")

    def extendMarkdown(self, md):
        md.preprocessors.register(WikilinkPreprocessor(self.WIKILINK_RE), 'wikilink', 100)


class WikilinkPreprocessor(Preprocessor):
    def __init__(self, regex):
        super().__init__()
        self.regex = regex

    def run(self, lines):
        return [self.regex.sub(self._sostituisci, line) for line in lines]

    def _sostituisci(self, match):
        destinazione = match.group(1).strip()
        etichetta = (match.group(2) or destinazione).strip()
        # Risoluzione per nome (semantica Obsidian): se la nota esiste da qualche
        # parte nel vault, il link va al suo percorso reale; altrimenti resta il
        # tentativo alla radice, che la route trasformerà in 404 onesto.
        chiave = destinazione.lower()
        relativo = INDICE_WIKILINK[chiave] if chiave in INDICE_WIKILINK else destinazione + '.md'
        url = '/visualizza/' + urllib.parse.quote(relativo)
        return f'[{etichetta}]({url})'


EXTENSIONI = ['fenced_code', 'tables', 'toc', 'codehilite', 'def_list', 'attr_list', WikilinkExtension()]


def html_pagina(titolo, contenuto, mtime=None):
    # data-mtime: il JS di auto-refresh confronta questo valore con quello del fetch
    # successivo; ricarica solo se il file è davvero cambiato (niente falsi reload).
    tag_body = f'<body data-mtime="{m}">' if (m := mtime) else '<body>'
    # titolo: interpolato in <title> e sempre escapato qui, in UN solo punto:
    # i chiamanti passano testo nudo (titolo di config, basename di file).
    titolo = html.escape(str(titolo))
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{titolo}</title>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 15px;
            background-color: #1e1e1e;
            color: #d4d4d4;
        }}
        h1, h2, h3 {{
            color: #ffffff;
            border-bottom: 1px solid #444444;
            padding-bottom: 5px;
        }}
        a {{ color: #6cb6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        ul.lista {{ list-style-type: none; padding: 0; }}
        ul.lista li {{
            background-color: #2a2a2a;
            margin-bottom: 10px;
            border-radius: 5px;
            border: 1px solid #444;
            transition: background-color 0.2s;
        }}
        ul.lista li:hover {{ background-color: #3c3c3c; }}
        ul.lista li a {{ display: block; padding: 12px 15px; font-weight: bold; }}

        .percorso {{ color: #888; font-size: 0.9em; }}
        .home-link {{
            display: block; margin-top: 30px; font-weight: bold;
            background-color: #333; padding: 10px; border-radius: 5px; text-align: center;
        }}

        pre {{ background-color: #141414; border: 1px solid #333; border-radius: 5px; padding: 12px; overflow-x: auto; }}
        code {{ background-color: #141414; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }}
        pre code {{ padding: 0; background: none; }}
        .codehilite {{ border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #444; padding: 8px 10px; text-align: left; }}
        th {{ background-color: #2a2a2a; }}
        tr:nth-child(even) td {{ background-color: #242424; }}
        blockquote {{ border-left: 4px solid #555; margin: 10px 0; padding: 2px 15px; color: #aaa; }}
        img {{ max-width: 100%; }}
        {CSS_PYGMENTS}
    </style>
</head>
{tag_body}
    {contenuto}
</body>
</html>"""


@app.route("/")
def homepage():
    try:
        sezioni = elenco_file()
    except NotADirectoryError:
        # os.walk su percorso inesistente tace e torna lista vuota ("nessun file"):
        # errore fuorviante. Qui fallisce rumoroso, col percorso colpevole.
        return html_pagina("Error", f"<h1>Error</h1><p>The folder '{html.escape(MD_ROOT)}' does not exist.</p>")
    # os.walk salta le directory nascoste (.obsidian, .debris, __pycache__…) prima
    # di elencarle: il viewer mostra solo contenuti reali.
    # escape su rel_dir e nome_file: arrivano dal filesystem (nomi file/pagine
    # syncati, non scritti da noi) e senza escape un '<img onerror=…>.md'
    # inietterebbe HTML in ogni homepage.
    contenuto = f"<h1>{html.escape(MD_TITLE)}</h1>"
    for rel_dir, files in sezioni:
        if rel_dir != '.':
            contenuto += f"<h2 class='percorso'>{html.escape(rel_dir)}/</h2>"
        lista = "<ul class='lista'>"
        for nome_file in files:
            rel = nome_file if rel_dir == '.' else os.path.join(rel_dir, nome_file)
            url = '/visualizza/' + urllib.parse.quote(rel)
            lista += f"<li><a href='{url}'>{html.escape(nome_file)}</a></li>"
        contenuto += lista + "</ul>"
    if len(sezioni) == 0:
        contenuto += "<p>No .md or .html files found.</p>"
    return html_pagina(MD_TITLE, contenuto)


def elenco_file():
    """Elenco ricorsivo dei .md/.html: [(cartella_relativa, [file…]), …] ordinato."""
    # Guardia esplicita: os.walk su directory mancante non alza nulla e
    # produce lista vuota — qui fallisce rumoroso perché la homepage
    # distingua "radice mancante" da "radice vuota".
    if not os.path.isdir(MD_ROOT):
        raise NotADirectoryError(MD_ROOT)
    sezioni = []
    for dirpath, dirnames, filenames in os.walk(MD_ROOT):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.') and d != '__pycache__')
        files = sorted(f for f in filenames
                       if f.lower().endswith(('.md', '.html', '.htm')) and not f.startswith('.'))
        if files:
            sezioni.append((os.path.relpath(dirpath, MD_ROOT), files))
    return sorted(sezioni)


@app.route("/visualizza/<path:percorso_rel>")
def visualizza(percorso_rel):
    radice = RADICE_REALE
    percorso = os.path.realpath(os.path.join(radice, percorso_rel))
    # realpath risolve '../' e symlink: se il risultato esce dalla radice, il file
    # non esiste "ai fini del viewer" → 404, mai lettura fuori da MD_ROOT.
    if not percorso.startswith(radice + os.sep) or not os.path.isfile(percorso):
        abort(404)
    basso = percorso.lower()
    if basso.endswith(('.html', '.htm')):
        # .html/.htm: byte-per-byte, nessun template — il file è già il documento
        # finito e l'agnostico lo rende fedele a sé stesso, non rifunzionale.
        with open(percorso, "rb") as f:
            risposta = app.response_class(f.read(), mimetype='text/html')
        risposta.headers['X-Document-Mtime'] = str(os.path.getmtime(percorso))
        return risposta
    with open(percorso, "r", encoding="utf-8") as f:
        aggiorna_indice_wikilink()
        # nh3 pulisce l'HTML prodotto dal markdown: il sorgente .md arriva dal
        # filesystem (cartelle syncate) e attr_list/raw HTML permettono attributi
        # arbitrari (onclick, script). Allowlist = default di nh3 + class/id su
        # ogni tag: toc e codehilite li usano (id="…", class="codehilite") e senza
        # class il highlighting non si colora più. Occhio: passare `attributes`
        # SOSTITUISCE i default (perderemmo href) — per questo si parte da
        # ALLOWED_ATTRIBUTES e si estende, non il contrario.
        attributi = dict(nh3.ALLOWED_ATTRIBUTES)
        attributi.setdefault('*', set()).update({'class', 'id'})
        contenuto_html = nh3.clean(markdown.markdown(f.read(), extensions=EXTENSIONI),
                                   attributes=attributi)
    rel = os.path.relpath(percorso, radice)
    mtime = os.path.getmtime(percorso)
    filaccio = f"<a class='home-link' href='/'>← Back to {html.escape(MD_TITLE)}</a>"
    return html_pagina(
        os.path.basename(percorso),
        f"<p class='percorso'>{html.escape(rel)}</p>" + contenuto_html + filaccio,
        mtime=str(mtime),
    )


@app.errorhandler(404)
def pagina_non_trovata(e):
    contenuto = "<h1>Error 404: Page not found</h1><p>The requested file does not exist.</p><a class='home-link' href='/'>← Back</a>"
    return html_pagina("Page not found", contenuto), 404


if __name__ == "__main__":
    print(f" * Espositore documenti (.md/.html): {MD_ROOT} → http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT)