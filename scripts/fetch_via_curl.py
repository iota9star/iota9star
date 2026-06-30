#!/usr/bin/env python3
"""Fetch repo star counts via curl + GitHub REST API, sort desc, emit masonry table."""
import json
import subprocess

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
    cmd = ["curl", "-s", "-m", "8", "-H", "User-Agent: iota9star-profile",
           "https://api.github.com/repos/{}".format(repo)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=12).stdout
        return int(json.loads(out).get("stargazers_count", 0))
    except Exception:
        return 0


def main():
    data = [(r, stars(r)) for r in REPOS]
    data.sort(key=lambda x: x[1], reverse=True)
    print("===SORTED===")
    for repo, s in data:
        print("{}\t{}".format(s, repo))
    print("===TABLE===")
    lines = ["<table>", "<tr>"]
    for i, (repo, _s) in enumerate(data):
        if i > 0 and i % 2 == 0:
            lines.append("</tr><tr>")
        link = "https://github.com/{}".format(repo)
        card = "https://gh-card.dev/repos/{}.svg".format(repo)
        lines.append('<td align="center"><a href="{}"><img src="{}" alt="{}" /></a></td>'.format(link, card, repo))
    if len(data) % 2 != 0:
        lines.insert(-1, "<td></td>")
    lines.append("</tr>")
    lines.append("</table>")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
