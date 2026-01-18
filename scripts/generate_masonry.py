#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Calculator

A tool for calculating masonry/waterfall layout positions for GitHub project cards.
Called by Claude Code Action to provide layout data for README generation.

Usage:
    python scripts/generate_masonry.py owner/repo1 owner/repo2 ...

Output:
    JSON with layout data for each repo card
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import sys
import json
from pathlib import Path
from typing import List, Tuple, Dict


def download_svg(repo: str, temp_dir: Path) -> Tuple[Path, Tuple[int, int]]:
    """Download gh-card SVG and parse its dimensions."""
    owner, name = repo.split("/")
    filename = f"{owner}-{name}.svg"
    filepath = temp_dir / filename
    url = f"https://gh-card.dev/repos/{repo}.svg"

    try:
        urllib.request.urlretrieve(url, filepath)
        width, height = parse_svg_size(filepath)
        return filepath, (width, height)
    except urllib.error.URLError as e:
        print(f"Failed to download {repo}: {e}", file=sys.stderr)
        return None, (400, 200)  # Fallback dimensions


def parse_svg_size(filepath: Path) -> Tuple[int, int]:
    """Parse width and height from SVG file."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Try width/height attributes
        width = root.get("width")
        height = root.get("height")

        if width and height:
            width = int(width.rstrip("px"))
            height = int(height.rstrip("px"))
            return width, height

        # Try viewBox attribute
        viewbox = root.get("viewBox")
        if viewbox:
            _, _, width, height = map(float, viewbox.split())
            return int(width), int(height)

        return 400, 200  # Default

    except Exception:
        return 400, 200


def calculate_masonry(repos: List[str]) -> Dict:
    """
    Calculate masonry layout for given repos.

    Returns dict with:
    - viewbox_width: SVG viewBox width (800 for 400px columns)
    - viewbox_height: SVG viewBox height (total layout height)
    - cards: list of card data with positions
    """
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    column_width = 400  # Width of each column in pixels
    gap = 8  # Gap between cards in pixels
    left_y = 0
    right_y = 0

    cards = []

    for repo in repos:
        filepath, (width, height) = download_svg(repo, temp_dir)

        if left_y <= right_y:
            # Place in left column
            x = 0
            y = left_y
            left_y += height + gap
        else:
            # Place in right column
            x = column_width
            y = right_y
            right_y += height + gap

        cards.append({
            "repo": repo,
            "x": x,
            "y": y,
            "width": column_width,
            "height": height,
            "url": f"https://gh-card.dev/repos/{repo}.svg"
        })

    viewbox_height = max(left_y, right_y)
    viewbox_width = column_width * 2

    return {
        "viewbox_width": viewbox_width,
        "viewbox_height": viewbox_height,
        "total_height": viewbox_height,
        "cards": cards
    }


def main():
    """Main entry point - CLI mode."""
    if len(sys.argv) < 2:
        print("Usage: python generate_masonry.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: HTML div with CSS columns for masonry layout", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]

    # Download to get card data (needed for display)
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    cards = []
    for repo in repos:
        filepath, (width, height) = download_svg(repo, temp_dir)
        cards.append({
            "repo": repo,
            "url": f"https://gh-card.dev/repos/{repo}.svg"
        })

    # Generate HTML with CSS columns
    print('<div style="column-count: 2; column-gap: 8px;">')
    for card in cards:
        print(f'<a href="https://github.com/{card["repo"]}"><img src="{card["url"]}" width="400"/></a>')
    print('</div>')


if __name__ == "__main__":
    main()
