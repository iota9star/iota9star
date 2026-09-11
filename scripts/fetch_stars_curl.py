#!/usr/bin/env python3
"""Fetch star counts via GitHub REST API (curl fallback for gh CLI),
then emit the same 2-column HTML table as generate_masonry.py."""

import json
import subprocess
import sys
import urllib.request

REPOS = [
    "fluttercandies/fjs",
    "fluttercandies/hora",
    "fluttercandies/dpad",
    "fluttercandies/resx",
    "fluttercandies/f_limit",
    "fluttercandies/json_dart",
    "fluttercandies/env2dart",
    "fluttercandies/flexbox_layout",
    "fluttercandies/dotrix",
    "fluttercandies/dash_router",
    "fluttercandies/vcard_dart",
    "fluttercandies/svgo",
    "void-signals/void_signals",
    "iota9star/mikan_flutter",
    "iota9star/sakura-dmhy",
    "iota9star/kisssub",
]


def fetch_repo(repo: str):
    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-gen"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.load(resp)
            return {
                "repo": repo,
                "stars": int(data.get("stargazers_count", 0)),
                "desc": (data.get("description") or "").strip(),
                "lang": data.get("language") or "",
            }
        except Exception:
            if attempt == 2:
                return {"repo": repo, "stars": 0, "desc": "", "lang": ""}


def main():
    repos = sys.argv[1:] or REPOS
    infos = [fetch_repo(r) for r in repos]
    infos.sort(key=lambda x: x["stars"], reverse=True)

    for info in infos:
        print(f"{info['stars']:>6}  {info['repo']:<32} [{info['lang']}] {info['desc']}", file=sys.stderr)

    cards = []
    for info in infos:
        repo = info["repo"]
        cards.append(
            f'<a href="https://github.com/{repo}">'
            f'<img src="https://gh-card.dev/repos/{repo}.svg" alt="{repo}" /></a>'
        )

    lines = ["<table>", "<tr>"]
    for i, html in enumerate(cards):
        if i > 0 and i % 2 == 0:
            lines.append("</tr><tr>")
        lines.append(f'<td align="center">{html}</td>')
    lines.append("</tr>")
    if len(cards) % 2 != 0:
        lines.insert(-1, "<td></td>")
    lines.append("</table>")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
