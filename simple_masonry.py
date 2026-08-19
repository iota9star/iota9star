#!/usr/bin/env python3
"""
Simple GitHub Profile Masonry Generator
Uses gh-card.dev URLs directly without requiring gh CLI authentication
"""

import sys

# Repository list
repos = [
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
    "iota9star/kisssub"
]

def generate_masonry_markdown():
    """Generate markdown with gh-card.dev URLs"""
    for repo in repos:
        card_url = f"https://gh-card.dev/repos/{repo}.svg"
        repo_link = f"https://github.com/{repo}"
        print(f'[![]({card_url})]({repo_link})')

if __name__ == "__main__":
    generate_masonry_markdown()
