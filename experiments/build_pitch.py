"""Render docs/pitch/technical_note.md to HTML and, if a Chromium browser is installed, to PDF."""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "pitch" / "technical_note.md"
HTML = SRC.with_suffix(".html")
PDF = ROOT / "docs" / "pitch" / "QuakeScore_technical_note.pdf"

CSS = """
@page { size: A4; margin: 17mm 16mm 17mm 16mm; }
html { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 9.6pt; line-height: 1.42; color: #0b0b0b; }
body { margin: 0; }
h1 { font-size: 20pt; margin: 0 0 2mm; letter-spacing: -0.01em; }
h2 { font-size: 12.5pt; margin: 6mm 0 1.5mm; break-after: avoid; }
h3 { font-size: 10.2pt; margin: 4mm 0 1mm; break-after: avoid; }
p { margin: 0 0 2.2mm; }
ul, ol { margin: 0 0 2.2mm; padding-left: 5mm; }
li { margin-bottom: 0.8mm; }
table { border-collapse: collapse; width: 100%; margin: 1.5mm 0 3mm; font-size: 8.4pt; break-inside: avoid; }
th { text-align: left; font-weight: 600; color: #52514e; border-bottom: 0.8pt solid #b9b8b2; padding: 1.2mm 1.6mm; }
td { border-bottom: 0.4pt solid #e4e3de; padding: 1.1mm 1.6mm; vertical-align: top; }
img { max-width: 100%; display: block; margin: 2mm auto 1mm; break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 8.6pt; }
blockquote { margin: 2mm 0 3mm; padding: 2mm 3.5mm; background: #f3f2ee; border-radius: 2.5mm; break-inside: avoid; }
blockquote p:last-child { margin-bottom: 0; }
.lede { font-size: 11pt; color: #52514e; margin-bottom: 4mm; }
.pagebreak { break-before: page; }
em.label { font-style: normal; font-size: 7.6pt; font-weight: 600; letter-spacing: 0.04em; padding: 0.3mm 1.6mm; border-radius: 1.6mm;
           background: #fff1d6; color: #7a4b00; white-space: nowrap; }
"""


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "attr_list", "md_in_html"])
    body = re.sub(r"\[(SIM|REAL|REF|ASSUMED)\]", r'<em class="label">\1</em>', body)
    HTML.write_text(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>QuakeScore technical note</title>"
                    f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
    browser = next((p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                                shutil.which("chromium") or "", shutil.which("google-chrome") or "") if p and pathlib.Path(p).exists()), None)
    if browser is None:
        print("HTML written; no Chromium browser found for PDF")
        return 0
    subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={PDF}", HTML.as_uri()],
                   check=True, capture_output=True, timeout=120)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", PDF.read_bytes()))
    print(f"PDF written: {PDF.name}, {pages} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
