#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator

Generates Markdown table with project cards.
GitHub renders images natively without SVG complications.

Usage:
    python scripts/generate_masonry.py owner/repo1 owner/repo2 ...

Output:
    Markdown with table layout
"""

import sys
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Tuple


CARDS_DIR = Path("cards")


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


def generate_masonry_markdown(repos: List[str]) -> str:
    """
    Download SVG files and generate Markdown with table layout.

    Returns Markdown with local SVG file references.
    """
    CARDS_DIR.mkdir(exist_ok=True)

    # Fetch and sort repos
    sorted_repos = fetch_and_sort_repos(repos)

    # Download all SVG files and prepare markdown
    cards_md = []
    for repo, stars, desc in sorted_repos:
        # Download SVG file
        svg_path = download_svg(repo)

        # Get relative path from repo root
        rel_path = str(svg_path)

        # Generate Markdown: [![](svg)](repo_link)
        repo_link = f"https://github.com/{repo}"
        cards_md.append(f'[![]({rel_path})]({repo_link})')

    # Create 2-column table layout
    lines = ['<table>', '<tr>']
    for i, md in enumerate(cards_md):
        if i > 0 and i % 2 == 0:
            lines.append('</tr><tr>')
        lines.append(f'<td align="center">{md}</td>')
    lines.append('</tr>')

    # Handle odd number of cards
    if len(cards_md) % 2 != 0:
        lines.insert(-1, '<td></td>')

    lines.append('</table>')
    return '\n'.join(lines)


def main():
    """Main entry point - CLI mode."""
    if len(sys.argv) < 2:
        print("Usage: python generate_masonry.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: Markdown with table layout", file=sys.stderr)
        print("\nFeatures:", file=sys.stderr)
        print("  - Fetches star counts via gh CLI", file=sys.stderr)
        print("  - Sorts repos by stars (descending)", file=sys.stderr)
        print("  - Downloads SVG files to cards/ directory", file=sys.stderr)
        print("  - Generates 2-column table layout", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]
    markdown = generate_masonry_markdown(repos)
    print(markdown)


if __name__ == "__main__":
    main()
