"""Build Campus_Equipment_DBMS_Study_Guide.pdf from study_guide_source.md.

Needs (in any virtualenv, not the app's): pip install weasyprint markdown pygments
WeasyPrint also needs Pango (macOS: brew install pango). Run from anywhere:
    python study_guide_build/build_guide.py
"""
import os
import re

import markdown
from pygments.formatters import HtmlFormatter
from weasyprint import HTML

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

COVER = """
<section class="cover">
  <div class="cover-band">
    <p class="kicker">DBMS Course · Project Study Guide</p>
    <h1 class="cover-title">Campus Equipment &amp; Lab Instrument Reservation</h1>
    <p class="cover-sub">with Maintenance Ledger</p>
  </div>
  <div class="cover-body">
    <p class="lead">A step-by-step guide to how the project works, from the six-table MySQL schema and its
    ER diagram to every important SQL query, the Flask code that runs it, and the questions to expect in a viva.</p>
    <div class="stack">
      <span>Python 3</span><span>Flask</span><span>Jinja</span><span>MySQL 8 · InnoDB</span>
      <span>mysql-connector-python</span><span>HTML / CSS</span><span>unittest</span>
    </div>
    <div class="tables-strip">
      <div class="t t-users">users</div><div class="t t-labs">labs</div><div class="t t-categories">categories</div>
      <div class="t t-equipment">equipment</div><div class="t t-reservations">reservations</div>
      <div class="t t-maintenance">maintenance_records</div>
    </div>
    <div class="cover-stats">
      <div><b>13</b>chapters</div><div><b>12</b>figures</div><div><b>21</b>routes traced</div><div><b>36</b>viva questions</div>
    </div>
    <p class="cover-note">Written from the project's actual source files: <code>app.py</code>, <code>db.py</code>,
    <code>schema.sql</code>, <code>reports.sql</code>, <code>seed.py</code>, templates and tests.
    Results quoted as observed were produced by running the project.</p>
  </div>
  <p class="cover-foot">Undergraduate Computer Science · Database Management Systems · October 2026</p>
</section>
"""


def number_headings(html):
    """Prefix chapter (h1) and section (h2) numbers and collect a table of contents."""
    toc, ch, sec = [], 0, 0

    def h1(m):
        nonlocal ch, sec
        ch, sec = ch + 1, 0
        toc.append((1, m.group(1), f"{ch}", m.group(2)))
        return f'<h1 id="{m.group(1)}"><span class="num">{ch}</span> {m.group(2)}</h1>'

    def h2(m):
        nonlocal sec
        sec += 1
        toc.append((2, m.group(1), f"{ch}.{sec}", m.group(2)))
        return f'<h2 id="{m.group(1)}"><span class="num">{ch}.{sec}</span> {m.group(2)}</h2>'

    # Single pass in document order so section numbers follow their chapter.
    def any_h(m):
        return h1(m) if m.group(0).startswith("<h1") else h2(m)

    html = re.sub(r'<h[12] id="([^"]+)">(.*?)</h[12]>', any_h, html)
    return html, toc


def toc_html(toc):
    rows = []
    for level, anchor, num, title in toc:
        rows.append(f'<li class="toc-{level}"><a href="#{anchor}"><span class="num">{num}</span> {title}</a></li>')
    return '<section class="toc"><h1 class="toc-title">Contents</h1><ul>' + "".join(rows) + "</ul></section>"


def main():
    with open(os.path.join(ROOT, "study_guide_source.md")) as f:
        source = f.read()
    body = markdown.markdown(source, extensions=["extra", "codehilite", "toc", "sane_lists"],
                             extension_configs={"codehilite": {"guess_lang": False, "css_class": "code"}})
    body, toc = number_headings(body)
    # Column-definition tables (header starts with "Column") get fixed widths so Purpose is readable.
    body = body.replace("<table>\n<thead>\n<tr>\n<th>Column</th>", '<table class="schema">\n<thead>\n<tr>\n<th>Column</th>')
    # Viva questions are h3 inside the viva chapter: give them a class for styling.
    body = re.sub(r'<h3 id="(q\d+[^"]*)">', r'<h3 class="q" id="\1">', body)
    with open(os.path.join(HERE, "guide.css")) as f:
        css = f.read() + HtmlFormatter(style="friendly").get_style_defs(".code")
        # Pygments marks characters such as "…" as errors with a red box; show them as plain text.
        css += "\n.code .err { border: none; color: inherit; background: none; }"
    html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Campus Equipment DBMS Study Guide"
            f"</title><style>{css}</style></head><body>{COVER}{toc_html(toc)}<main>{body}</main></body></html>")
    with open(os.path.join(HERE, "guide.html"), "w") as f:
        f.write(html)
    out = os.path.join(ROOT, "Campus_Equipment_DBMS_Study_Guide.pdf")
    HTML(string=html, base_url=ROOT).write_pdf(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
