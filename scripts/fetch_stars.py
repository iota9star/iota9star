#!/usr/bin/env python3
"""Fetch repo star counts via GitHub REST API (urllib, no gh), sort desc, print cards."""
import json
import urllib.request

REPOS = [
    "fluttercandies/fjs", "fluttercandies/hora", "fluttercandies/dpad",
    "fluttercandies/resx", "fluttercandies/f_limit", "fluttercandies/json_dart",
    "fluttercandies/env2dart", "fluttercandies/flexbox_layout",
    "fluttercandies/dotrix", "fluttercandies/dash_router",
    "fluttercandies/vcard_dart", "fluttercandies/svgo",
    "void-signals/void_signals", "iota9star/mikan_flutter",
    "iota9star/sakura-dmhy", "iota9star/kisssub",
]


def stars(repo):
    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "iota9star-profile",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return int(json.load(r).get("stargazers_count", 0))
    except Exception:
        return 0


def main():
    data = [(r, stars(r)) for r in REPOS]
    data.sort(key=lambda x: x[1], reverse=True)
    for repo, s in data:
        print(f"{s}\t{repo}")
    print("---TABLE---")
    lines = ["<table>", "<tr>"]
    for i, (repo, _s) in enumerate(data):
        if i > 0 and i % 2 == 0:
            lines.append("</tr><tr>")
        link = f"https://github.com/{repo}"
        card = f"https://gh-card.dev/repos/{repo}.svg"
        lines.append(f'<td align="center"><a href="{link}"><img src="{card}" alt="{repo}" /></a></td>')
    if len(data) % 2 != 0:
        lines.insert(-1, "<td></td>")
    lines.append("</tr>")
    lines.append("</table>")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
