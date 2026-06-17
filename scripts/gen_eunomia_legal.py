#!/usr/bin/env python3
"""Generate Eunomia legal HTML pages from the CBTapp markdown sources.

Produces, for both Terms of Service and Privacy Policy, an EN page plus
PL/FR/DE convenience translations, all sharing the Studio Volt CSS template
and a language switcher. Run from anywhere; paths are absolute.
"""
import html
import re
import os

CBT = "/Users/joannabednarczyk/projekty/CBTapp/legal"
OUT = "/Users/joannabednarczyk/projekty/studiovolt-dev/eunomia"

# --- shared CSS (lifted verbatim from the existing eunomia/terms.html) ---
CSS = """
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #0a0a0a; color: #e2e8f0; min-height: 100vh;
      }
      .header { padding: 2rem; text-align: center; border-bottom: 1px solid #1e1e1e; }
      .header h1 { font-size: 1.5rem; font-weight: 800; }
      .header h1 span { color: #98ffd9; }
      .header p { color: #94a3b8; margin-top: 0.25rem; font-size: 0.9rem; }
      .nav {
        display: flex; gap: 1.5rem; justify-content: center; flex-wrap: wrap;
        padding: 1rem; border-bottom: 1px solid #1e1e1e;
      }
      .nav a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; transition: color 0.2s; }
      .nav a:hover, .nav a.active { color: #98ffd9; }
      .langbar {
        display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;
        padding: 0.75rem 1rem; border-bottom: 1px solid #1e1e1e; background: #0d0d0d;
      }
      .langbar a { color: #64748b; text-decoration: none; font-size: 0.82rem; transition: color 0.2s; }
      .langbar a:hover { color: #98ffd9; }
      .langbar a.active { color: #98ffd9; font-weight: 600; }
      .content { max-width: 720px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
      .content h2 { font-size: 1.3rem; font-weight: 700; margin: 2rem 0 0.5rem; color: #f8fafc; }
      .content h3 { font-size: 1rem; font-weight: 600; margin: 1.5rem 0 0.5rem; color: #e2e8f0; }
      .content h4 { font-size: 0.95rem; font-weight: 600; margin: 1.25rem 0 0.4rem; color: #cbd5e1; }
      .content p { color: #cbd5e1; line-height: 1.7; margin-bottom: 1rem; font-size: 0.95rem; }
      .content ul, .content ol {
        color: #cbd5e1; line-height: 1.7; margin-bottom: 1rem; padding-left: 1.5rem; font-size: 0.95rem;
      }
      .content li { margin-bottom: 0.4rem; }
      .content strong { color: #f8fafc; }
      blockquote {
        border-left: 3px solid #98ffd9; background: #111827; border-radius: 8px;
        padding: 0.75rem 1rem; margin: 1rem 0; color: #cbd5e1;
      }
      blockquote p { margin-bottom: 0.5rem; }
      blockquote p:last-child { margin-bottom: 0; }
      .crisis {
        background: #2a1414; border: 1px solid #5b2424; border-left: 4px solid #fca5a5;
        border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0 2rem;
      }
      .crisis h3 { color: #fca5a5; margin-top: 0; font-size: 1.05rem; }
      .crisis p { color: #f1d6d6; }
      .crisis ul { color: #f1d6d6; margin-bottom: 0; }
      .crisis strong { color: #ffffff; }
      .transnote {
        background: #111827; border: 1px solid #1f2937; border-left: 4px solid #64748b;
        border-radius: 10px; padding: 1rem 1.25rem; margin: 1.5rem 0; font-size: 0.85rem;
      }
      .transnote p { color: #94a3b8; margin: 0; }
      .date { color: #64748b; font-size: 0.85rem; margin-bottom: 1.5rem; }
      .version { color: #64748b; font-size: 0.85rem; }
      hr { border: none; border-top: 1px solid #1e1e1e; margin: 2rem 0; }
      footer {
        text-align: center; padding: 2rem; font-size: 0.8rem; color: #475569;
        border-top: 1px solid #1e1e1e;
      }
      footer .made { margin-top: 0.4rem; color: #64748b; }
      a { color: #98ffd9; }
"""

# language metadata
LANGS = ["en", "pl", "fr", "de"]
LANG_LABEL = {"en": "English", "pl": "Polski", "fr": "Français", "de": "Deutsch"}

# per-language nav labels
NAV = {
    "en": {"app": "App", "privacy": "Privacy Policy", "terms": "Terms of Service"},
    "pl": {"app": "Aplikacja", "privacy": "Polityka prywatności", "terms": "Regulamin"},
    "fr": {"app": "App", "privacy": "Confidentialité", "terms": "CGU"},
    "de": {"app": "App", "privacy": "Datenschutz", "terms": "Nutzungsbedingungen"},
}

# headers (the <p> subtitle under the logo)
SUBTITLE = {
    "terms": {"en": "Terms of Service", "pl": "Regulamin", "fr": "Conditions Générales d'Utilisation", "de": "Nutzungsbedingungen"},
    "privacy": {"en": "Privacy Policy", "pl": "Polityka prywatności", "fr": "Politique de confidentialité", "de": "Datenschutzerklärung"},
}

TITLE = {
    "terms": "Terms of Service",
    "privacy": "Privacy Policy",
}

# source filename mapping
def src_path(doc, lang):
    base = "TERMS_OF_SERVICE" if doc == "terms" else "PRIVACY_POLICY"
    suffix = "" if lang == "en" else f".{lang}"
    return os.path.join(CBT, f"{base}{suffix}.md")

def out_path(doc, lang):
    suffix = "" if lang == "en" else f".{lang}"
    return os.path.join(OUT, f"{doc}{suffix}.html")


def inline(text):
    """Convert markdown inline (bold, links, code) to HTML, escaping the rest."""
    # protect by tokenizing bold / links / code first
    tokens = []

    def stash(htmlfrag):
        tokens.append(htmlfrag)
        return f"\x00{len(tokens)-1}\x00"

    # links [text](url)
    def link_repl(m):
        label = html.escape(m.group(1))
        url = m.group(2)
        return stash(f'<a href="{html.escape(url)}" rel="noopener" target="_blank">{label}</a>')
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, text)

    # bold **x**
    def bold_repl(m):
        return stash(f"<strong>{html.escape(m.group(1))}</strong>")
    text = re.sub(r"\*\*([^*]+)\*\*", bold_repl, text)

    # inline code `x`
    def code_repl(m):
        return stash(f"<code>{html.escape(m.group(1))}</code>")
    text = re.sub(r"`([^`]+)`", code_repl, text)

    # escape remaining text
    text = html.escape(text)

    # restore tokens
    def restore(m):
        return tokens[int(m.group(1))]
    text = re.sub(r"\x00(\d+)\x00", restore, text)
    return text


def md_to_blocks(md):
    """Parse markdown into a list of (type, payload) blocks."""
    lines = md.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped == "":
            i += 1
            continue
        if stripped == "---":
            blocks.append(("hr", None))
            i += 1
            continue
        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            blocks.append((f"h{level}", m.group(2)))
            i += 1
            continue
        # blockquote
        if stripped.startswith(">"):
            qlines = []
            while i < n and lines[i].strip().startswith(">"):
                qlines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append(("quote", qlines))
            continue
        # list (- )
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).rstrip())
                i += 1
            blocks.append(("ul", items))
            continue
        # paragraph (gather consecutive non-blank, non-special lines)
        plines = [line.rstrip()]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (nxt == "" or nxt == "---" or nxt.startswith("#")
                    or nxt.startswith(">") or re.match(r"^[-*]\s+", nxt)):
                break
            plines.append(lines[i].rstrip())
            i += 1
        blocks.append(("p", " ".join(plines)))
    return blocks


def render_body(blocks, doc):
    """Render blocks to HTML. h2-level sections in the source become h3 in
    the page (matching the existing template, where h1 is the doc title h2).
    Special-cases the crisis box and the convenience-translation note."""
    out = []
    # We will detect the "Important notice" / "Important — who ... is for"
    # sections and wrap them in callout boxes to match the original design.
    n = len(blocks)
    i = 0
    # skip leading H1 (doc title) — rendered separately in header/content top
    # We still emit version + date paragraphs and the translation note.
    while i < n:
        typ, payload = blocks[i]

        # H1 -> document title (only first); render as h2
        if typ == "h1":
            out.append(f"      <h2>{inline(payload)}</h2>")
            i += 1
            continue

        # the convenience-translation blockquote right after H1
        if typ == "quote":
            joined = " ".join(inline(p) for p in payload if p.strip())
            # Heuristic: translation note mentions "governs"/"prévaut"/"massgeblich"/"wiążąca"
            if re.search(r"convenience translation|traduction de courtoisie|Übersetzung zu Informationszwecken|tłumaczenie ma charakter informacyjny", joined):
                out.append(f'      <div class="transnote"><p>{joined}</p></div>')
            else:
                inner = "".join(f"<p>{inline(p)}</p>" for p in payload if p.strip())
                out.append(f"      <blockquote>{inner}</blockquote>")
            i += 1
            continue

        # H2 heading -> becomes a section h3 (template style)
        if typ == "h2":
            # Crisis/important-notice and audience boxes: detect by the next blocks
            heading = payload
            is_crisis = bool(re.search(r"Important notice|Ważna informacja|Avis important|Wichtiger Hinweis", heading))
            is_audience = bool(re.search(r"who Eunomia is for|dla kogo|à qui s'adresse|für wen Eunomia", heading))
            if is_crisis:
                # gather until next hr
                j = i + 1
                inner = [f'        <h3>&#9888; {inline(heading)}</h3>']
                while j < n and blocks[j][0] != "hr" and blocks[j][0] not in ("h1", "h2"):
                    inner.append("    " + render_one(blocks[j]))
                    j += 1
                out.append('      <div class="crisis">')
                out.extend(inner)
                out.append("      </div>")
                i = j
                continue
            # normal section heading
            out.append(f"      <h3>{inline(heading)}</h3>")
            i += 1
            continue

        if typ == "h3":
            out.append(f"      <h4>{inline(payload)}</h4>")
            i += 1
            continue
        if typ == "h4":
            out.append(f"      <h4>{inline(payload)}</h4>")
            i += 1
            continue

        out.append("      " + render_one(blocks[i]))
        i += 1
    return "\n".join(out)


def render_one(block):
    typ, payload = block
    if typ == "hr":
        return "<hr />"
    if typ == "p":
        # version + date block: "**Version 1.6** **Last updated: ...**" merged
        m = re.match(r"^(\*\*(?:Version|Wersja)[^*]*\*\*)\s+(\*\*(?:Last updated|Ostatnia aktualizacja|Dernière mise à jour|Zuletzt aktualisiert)[^*]*\*\*)$", payload)
        if m:
            return (f'<p class="version">{inline(m.group(1))}</p>\n'
                    f'      <p class="date">{inline(m.group(2))}</p>')
        if re.match(r"^\*\*(Version|Wersja)[^*]*\*\*$", payload):
            return f'<p class="version">{inline(payload)}</p>'
        if re.match(r"^\*\*(Last updated|Ostatnia aktualizacja|Dernière mise à jour|Zuletzt aktualisiert)[^*]*\*\*$", payload):
            return f'<p class="date">{inline(payload)}</p>'
        return f"<p>{inline(payload)}</p>"
    if typ == "ul":
        items = "\n        ".join(f"<li>{inline(it)}</li>" for it in payload)
        return f"<ul>\n        {items}\n      </ul>"
    if typ == "quote":
        inner = "".join(f"<p>{inline(p)}</p>" for p in payload if p.strip())
        return f"<blockquote>{inner}</blockquote>"
    if typ.startswith("h"):
        lvl = "h4"
        return f"<{lvl}>{inline(payload)}</{lvl}>"
    return ""


def langbar(doc, lang):
    parts = []
    for L in LANGS:
        suffix = "" if L == "en" else f".{L}"
        href = f"/eunomia/{doc}{suffix}.html"
        cls = ' class="active"' if L == lang else ""
        parts.append(f'      <a href="{href}"{cls}>{LANG_LABEL[L]}</a>')
    return "\n".join(parts)


def navbar(doc, lang):
    suffix = "" if lang == "en" else f".{lang}"
    nav = NAV[lang]
    priv_active = ' class="active"' if doc == "privacy" else ""
    terms_active = ' class="active"' if doc == "terms" else ""
    items = [
        f'      <a href="/eunomia/">{nav["app"]}</a>',
        f'      <a href="/eunomia/privacy{suffix}.html"{priv_active}>{nav["privacy"]}</a>',
        f'      <a href="/eunomia/terms{suffix}.html"{terms_active}>{nav["terms"]}</a>',
    ]
    return "\n".join(items)


def build(doc, lang):
    md = open(src_path(doc, lang), encoding="utf-8").read()
    blocks = md_to_blocks(md)
    body = render_body(blocks, doc)
    page_title = f"{TITLE[doc]} &mdash; Eunomia &mdash; Studio Volt"
    subtitle = SUBTITLE[doc][lang]
    html_out = f"""<!doctype html>
<html lang="{lang}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{page_title}</title>
    <style>{CSS}    </style>
  </head>
  <body>
    <div class="header">
      <h1>Eunomia<span>.</span></h1>
      <p>{html.escape(subtitle)}</p>
    </div>
    <nav class="nav">
{navbar(doc, lang)}
    </nav>
    <div class="langbar">
{langbar(doc, lang)}
    </div>
    <div class="content">
{body}
    </div>
    <footer>
      &copy; 2026 Studio Volt &middot; <a href="/">studiovolt.dev</a>
      <div class="made">Made in Switzerland &#127464;&#127469; by Joanna Bednarczyk</div>
    </footer>
  </body>
</html>
"""
    with open(out_path(doc, lang), "w", encoding="utf-8") as f:
        f.write(html_out)
    return out_path(doc, lang)


if __name__ == "__main__":
    for doc in ("terms", "privacy"):
        for lang in LANGS:
            p = build(doc, lang)
            print("wrote", p)
