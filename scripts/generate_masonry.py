#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator

Generates SVG with masonry (waterfall) layout using CSS columns.
The SVG can be embedded in GitHub README.

Usage:
    python scripts/generate_masonry.py owner/repo1 owner/repo2 ...

Output:
    SVG file with masonry layout
"""

import sys
import subprocess
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple


CARDS_DIR = Path("cards")
CARD_WIDTH = 380  # gh-card width
CARD_HEIGHT = 120  # approximate height per card
COLUMN_GAP = 8    # gap between columns
COLUMN_COUNT = 2  # number of columns
PADDING = 8       # container padding


def fetch_repo_info(repo: str, max_retries: int = 2) -> Tuple[str, int, str]:
    """Fetch repository info using gh CLI with retry logic."""
    cmd = [
        "gh", "repo", "view", repo,
        "--json", "stargazerCount,description,name",
        "--jq", '"\\(.name) | \\(.stargazerCount) | \\(.description)"'
    ]

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(" | ", 2)
                if len(parts) == 3:
                    return repo, int(parts[1]), parts[2]
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            if attempt < max_retries:
                continue
            break

    return repo, 0, ""


def download_svg(repo: str) -> Path:
    """Download SVG file and return local path."""
    CARDS_DIR.mkdir(exist_ok=True)

    owner, name = repo.split("/")
    filename = f"{owner}_{name}.svg"
    filepath = CARDS_DIR / filename
    url = f"https://gh-card.dev/repos/{repo}.svg"

    try:
        urllib.request.urlretrieve(url, filepath)
    except urllib.error.URLError:
        pass  # Use existing file if download fails

    return filepath


def fetch_and_sort_repos(repos: List[str]) -> List[Tuple[str, int, str]]:
    """Fetch all repo info and sort by star count descending."""
    repo_data = []
    for repo in repos:
        repo_info = fetch_repo_info(repo)
        repo_data.append(repo_info)
    repo_data.sort(key=lambda x: x[1], reverse=True)
    return repo_data


def read_svg_content(filepath: Path) -> str:
    """Read SVG file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def calculate_svg_height(num_cards: int) -> int:
    """Calculate approximate SVG height based on number of cards."""
    cards_per_column = (num_cards + COLUMN_COUNT - 1) // COLUMN_COUNT
    return cards_per_column * (CARD_HEIGHT + COLUMN_GAP) + PADDING * 2


def generate_masonry_svg(repos: List[str]) -> str:
    """
    Download SVG files and generate masonry layout SVG using <image> elements.

    Returns SVG content with masonry layout.
    """
    CARDS_DIR.mkdir(exist_ok=True)

    # Fetch and sort repos
    sorted_repos = fetch_and_sort_repos(repos)

    # Download all SVG files
    card_paths = []
    for repo, stars, desc in sorted_repos:
        svg_path = download_svg(repo)
        card_paths.append((repo, svg_path))

    # Manual masonry layout: distribute cards across columns
    column_heights = [PADDING] * COLUMN_COUNT
    column_x = [PADDING + i * (CARD_WIDTH + COLUMN_GAP) for i in range(COLUMN_COUNT)]

    # Build SVG with <image> elements positioned manually
    images_svg = []
    for i, (repo, svg_path) in enumerate(card_paths):
        # Assign to column with minimum height (round-robin)
        col = i % COLUMN_COUNT

        # Position in column
        x = column_x[col]
        y = column_heights[col]

        # Get relative path from repo root
        rel_path = str(svg_path)

        # Create clickable wrapper (using <a> in SVG)
        repo_link = f"https://github.com/{repo}"
        images_svg.append(f'''  <a href="{repo_link}" target="_top">
    <image x="{x}" y="{y}" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" href="{rel_path}" />
  </a>''')

        # Update column height
        column_heights[col] += CARD_HEIGHT + COLUMN_GAP

    # Calculate SVG dimensions
    svg_width = CARD_WIDTH * COLUMN_COUNT + COLUMN_GAP * (COLUMN_COUNT - 1) + PADDING * 2
    svg_height = max(column_heights) + PADDING

    # Build SVG
    images_svg_str = '\n'.join(images_svg)

    svg_template = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">
{images_svg_str}
</svg>'''

    return svg_template


def generate_masonry_svg_file(repos: List[str], output_path: Path = None) -> Path:
    """
    Generate and save masonry SVG file.

    Returns path to the generated SVG file.
    """
    CARDS_DIR.mkdir(exist_ok=True)

    if output_path is None:
        output_path = CARDS_DIR / "masonry_layout.svg"

    svg_content = generate_masonry_svg(repos)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    return output_path


def main():
    """Main entry point - CLI mode."""
    if len(sys.argv) < 2:
        print("Usage: python generate_masonry.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: Markdown reference to generated masonry SVG", file=sys.stderr)
        print("\nFeatures:", file=sys.stderr)
        print("  - Fetches star counts via gh CLI", file=sys.stderr)
        print("  - Sorts repos by stars (descending)", file=sys.stderr)
        print("  - Downloads SVG files to cards/ directory", file=sys.stderr)
        print("  - Generates masonry layout SVG with CSS columns", file=sys.stderr)
        print("  - Embeds cards as data URIs (self-contained)", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]

    # Generate masonry SVG file
    svg_path = generate_masonry_svg_file(repos)

    # Output Markdown reference
    rel_path = str(svg_path)
    print(f'[![]({rel_path})](#)')


if __name__ == "__main__":
    main()
