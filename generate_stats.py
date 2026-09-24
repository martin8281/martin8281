#!/usr/bin/env python3
"""Generates stats.svg and languages.svg for a GitHub profile README.

Runs inside GitHub Actions (see .github/workflows/update-stats.yml) using the
built-in GITHUB_TOKEN, so it doesn't depend on any third-party stats server.
"""
import json
import os
import urllib.request
from xml.sax.saxutils import escape as e

USER = os.environ.get("GH_USER", "martin8281")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
FONT = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif"
LANG_COLORS = ["#a855f7", "#6366f1", "#c084fc", "#38bdf8", "#f0abfc", "#818cf8", "#8b5cf6", "#e879f9"]


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"},
    )
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        try:
            for lang, b in api(f"/repos/{USER}/{r['name']}/languages").items():
                langs[lang] = langs.get(lang, 0) + b
        except Exception:
            pass
    return {
        "repos": user["public_repos"],
        "followers": user["followers"],
        "stars": sum(r["stargazers_count"] for r in own),
        "forks": sum(r["forks_count"] for r in own),
        "langs": langs,
    }


def shell(title, body, uid):
    return f'''<svg width="480" height="200" viewBox="0 0 480 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{e(title)}">
<defs>
  <linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a1145"/><stop offset="1" stop-color="#0b0720"/></linearGradient>
  <linearGradient id="bd{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a855f7"/><stop offset="1" stop-color="#4f46e5"/></linearGradient>
  <radialGradient id="gl{uid}"><stop offset="0" stop-color="#8b5cf6" stop-opacity=".5"/><stop offset="1" stop-color="#8b5cf6" stop-opacity="0"/></radialGradient>
  <clipPath id="c{uid}"><rect x="1" y="1" width="478" height="198" rx="16"/></clipPath>
</defs>
<style>@keyframes p{{0%,100%{{opacity:.5}}50%{{opacity:1}}}}.g{{animation:p 3.6s ease-in-out infinite}}</style>
<rect x="1" y="1" width="478" height="198" rx="16" fill="url(#bg{uid})" stroke="url(#bd{uid})" stroke-width="1.5"/>
<g clip-path="url(#c{uid})"><circle class="g" cx="480" cy="0" r="150" fill="url(#gl{uid})"/></g>
<text x="24" y="38" font-family="{FONT}" font-size="15" font-weight="700" letter-spacing="1.4" fill="#c4b5fd">{e(title.upper())}</text>
<line x1="24" y1="52" x2="456" y2="52" stroke="#3b2a7a"/>
{body}
</svg>'''


def render_stats(d):
    items = [("Public repos", "repos"), ("Stars earned", "stars"), ("Followers", "followers"), ("Forks", "forks")]
    pos = [(24, 100), (250, 100), (24, 165), (250, 165)]
    out = []
    for (label, key), (x, y) in zip(items, pos):
        val = "–" if d is None else f"{d[key]:,}"
        out.append(f'<circle cx="{x+5}" cy="{y-9}" r="4" fill="#a855f7"/>')
        out.append(f'<text x="{x+18}" y="{y}" font-family="{FONT}" font-size="28" font-weight="700" fill="#f5f3ff">{val}</text>')
        out.append(f'<text x="{x+18}" y="{y+20}" font-family="{FONT}" font-size="12" fill="#a78bfa">{label}</text>')
    return shell("GitHub Overview", "\n".join(out), "s")


def render_langs(d):
    langs = {} if d is None else d["langs"]
    total = sum(langs.values())
    out = []
    if not total:
        out.append(f'<text x="24" y="110" font-family="{FONT}" font-size="13" fill="#a78bfa">Language data appears after the first workflow run.</text>')
        return shell("Top Languages", "\n".join(out), "l")
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    shown = sum(b for _, b in top)
    top_pct = [(n, b / total * 100) for n, b in top]
    out.append('<clipPath id="bar"><rect x="24" y="66" width="432" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    x = 24.0
    for i, (n, pct) in enumerate(top_pct):
        w = 432 * pct / 100
        out.append(f'<rect x="{x:.2f}" y="66" width="{w:.2f}" height="10" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>')
        x += w
    out.append("</g>")
    for i, (n, pct) in enumerate(top_pct):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 226, 108 + row * 26
        out.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>')
        out.append(f'<text x="{lx+18}" y="{ly}" font-family="{FONT}" font-size="13" fill="#e0e7ff">{e(n)}</text>')
        out.append(f'<text x="{lx+200}" y="{ly}" text-anchor="end" font-family="{FONT}" font-size="12" fill="#a78bfa">{pct:.1f}%</text>')
    return shell("Top Languages", "\n".join(out), "l")


def write(data):
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "stats.svg"), "w", encoding="utf-8").write(render_stats(data))
    open(os.path.join(here, "languages.svg"), "w", encoding="utf-8").write(render_langs(data))


if __name__ == "__main__":
    write(fetch())
    print("stats.svg and languages.svg updated")
