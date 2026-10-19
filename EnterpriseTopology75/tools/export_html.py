#!/usr/bin/env python3
"""Render the English Markdown guide as a local HTML page (requires Markdown)."""
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]
style = '''
:root{color-scheme:light;--ink:#1d1b20;--muted:#625b71;--accent:#6750a4;--line:#e7e0ec;--surface:#f7f2fa}
*{box-sizing:border-box}body{margin:0;background:#fef7ff;color:var(--ink);font:16px/1.7 system-ui,-apple-system,sans-serif}
main{max-width:1160px;margin:0 auto;padding:64px 32px 80px}header{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:32px}
header span{font-size:12px;letter-spacing:.12em;color:var(--accent);font-weight:700}header a{font-size:14px}
h1{font-size:clamp(32px,5vw,54px);line-height:1.12;letter-spacing:-.045em;max-width:850px;margin:0 0 24px}h2{font-size:26px;letter-spacing:-.025em;margin:48px 0 16px}
p,li{max-width:100%;}a{color:var(--accent);text-underline-offset:3px}img{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:16px;background:white}
pre{padding:24px;background:#211f26;color:#e6e0e9;border-radius:16px;overflow:auto;font-size:14px;line-height:1.8}code{font-family:ui-monospace,SFMono-Regular,monospace;font-size:.9em}p code,li code,td code{background:var(--surface);padding:2px 5px;border-radius:4px}
.table-scroll{overflow:auto;border:1px solid var(--line);border-radius:16px;margin:20px 0}table{border-collapse:collapse;width:100%;min-width:680px;font-size:14px}th,td{text-align:left;vertical-align:top;padding:14px 16px;border-bottom:1px solid var(--line)}th{background:var(--surface)}tr:last-child td{border:0}
.notice{padding:18px 22px;background:#eaddff;border-radius:16px;color:#21005d;margin-bottom:28px;font-size:14px}.footer{margin-top:48px;border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:13px}
@media(max-width:600px){main{padding:32px 18px}pre{padding:16px}h2{font-size:23px}}@media print{body{background:white}main{padding:0}header{display:none}pre{white-space:pre-wrap;background:#f3edf7;color:#1d1b20}}
'''
for source, output, title, prefix in [
    ('README.md','topology-guide.html','75-Device Enterprise Network',''),
    ('docs/validation.md','docs/validation.html','Validation Notes','../'),
]:
    content = markdown.markdown((ROOT/source).read_text(), extensions=['tables','fenced_code'])
    content = content.replace('<table>', '<div class="table-scroll"><table>').replace('</table>','</table></div>')
    content = content.replace('href="docs/validation.md"','href="docs/validation.html"')
    # The diagram remains in the page and opens at full size when selected.
    content = content.replace('<img alt="Complete 75-device enterprise network topology" src="docs/topology-75.png" />','<a href="docs/topology-75.svg" aria-label="Open the full-size topology diagram"><img alt="Complete 75-device enterprise network topology" src="docs/topology-75.png" /></a>')
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style>{style}</style></head>
<body><main><header><span>ENTERPRISE NETWORK / DOCUMENTATION</span><a href="{prefix}README.md" download>Download Markdown</a><a href="{prefix}docs/topology-75.svg">Full-size diagram</a></header><div class="notice">Standalone 75-device lab · Configuration and structural checks passed. Runtime validation is pending.</div>{content}<div class="footer">Generated from the English Markdown documentation. Physical links are shown; STP selects active Layer 2 paths.</div></main></body></html>
'''
    (ROOT/output).write_text(html)
    print(ROOT/output)
