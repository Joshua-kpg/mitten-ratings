#!/usr/bin/env python3
"""Build the Cloudflare Pages folder for Rim Runner (Michigan).

Copies the site files into _deploy/ and removes leftovers from Netlify hosting
(Netlify's injected comment/meta tags and its /.netlify/ analytics scripts, which
404 off Netlify) and points old netlify.app links at the new home. App code,
data and formula are not touched.

Usage: python3 scripts/cf_prepare.py [repo_dir] [out_dir]
"""
import re, shutil, sys
from pathlib import Path

NEW_URL = "https://rimrunner.pages.dev"
repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
out = Path(sys.argv[2] if len(sys.argv) > 2 else repo / "_deploy").resolve()
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

html = (repo / "index.html").read_text(encoding="utf-8")
before = len(html)
# Netlify-injected hosting comment + meta tags
html = re.sub(r"<!-- This site is hosted on Netlify\..*?-->\s*", "", html, flags=re.S)
html = re.sub(r'<meta name="hosting-provider" content="Netlify">\s*', "", html)
html = re.sub(r'<meta name="netlify-deploy"[^>]*>\n?', "", html)
# Netlify RUM / HUD scripts (served from /.netlify/, which does not exist on Cloudflare)
html = re.sub(r'\s*<script[^>]*src="/\.netlify/[^"]*"[^>]*>\s*</script>', "", html)
# Old domains -> new domain
html = html.replace("https://mittenrankings.netlify.app", NEW_URL)
html = html.replace("https://rimrunner.netlify.app/", NEW_URL + "/")
html = html.replace("rimrunner.netlify.app", "rimrunner.pages.dev")
if "netlify" in html.lower():
    left = sorted(set(m.group(0) for m in re.finditer(r".{0,40}netlify.{0,40}", html, re.I)))
    print("WARNING: netlify still mentioned:", *left, sep="\n  ")
(out / "index.html").write_text(html, encoding="utf-8")

for name in ["live-scores.json"] + [p.name for p in repo.glob("google*.html")]:
    if (repo / name).exists():
        shutil.copy2(repo / name, out / name)

# Team logos (logos/<team id>.webp + manifest.json), served from this same site. See HANDBOOK "Team logos".
if (repo / "logos").is_dir():
    shutil.copytree(repo / "logos", out / "logos")

# Same caching Netlify used: always revalidate, so pushes show up right away.
# Logos are fingerprinted in the page (?v=<version>), so browsers may keep them for a week.
(out / "_headers").write_text(
    "/*\n  Cache-Control: public, max-age=0, must-revalidate\n"
    "/live-scores.json\n  Cache-Control: no-store\n"
    "/logos/*\n  ! Cache-Control\n  Cache-Control: public, max-age=604800\n", encoding="utf-8")

print(f"Prepared {out} (index.html {before} -> {len(html)} bytes):",
      ", ".join(sorted(p.name for p in out.iterdir())),
      f"(logos: {len(list((out / 'logos').glob('*.webp'))) if (out / 'logos').exists() else 0})")
