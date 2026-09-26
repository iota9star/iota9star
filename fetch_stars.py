#!/usr/bin/env python3
"""Fetch star counts for the featured repos via the public GitHub API, sorted descending."""
import json
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


def fetch(repo: str) -> int:
    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-generator"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            return int(data.get("stargazers_count", 0))
    except Exception:
        return 0


def main() -> None:
    rows = [(fetch(r), r) for r in REPOS]
    rows.sort(reverse=True)
    for stars, repo in rows:
        print(f"{stars}\t{repo}")


if __name__ == "__main__":
    main()
