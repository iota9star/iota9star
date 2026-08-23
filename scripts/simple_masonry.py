#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator - Simple Version

Generates Markdown with local SVG card files without requiring gh CLI.
Downloads SVG files from gh-card.dev to cards/ directory.

Usage:
    python scripts/simple_masonry.py owner/repo1 owner/repo2 ...

Output:
    Markdown with local SVG references
"""

import sys
import urllib.request
import os
from typing import List


def download_svg(repo: str, cards_dir: str) -> str:
    """Download SVG card from gh-card.dev and save locally."""
    card_url = f"https://gh-card.dev/repos/{repo}.svg"
    local_filename = f"{repo.replace('/', '_')}.svg"
    local_path = os.path.join(cards_dir, local_filename)

    try:
        urllib.request.urlretrieve(card_url, local_path)
        print(f"Downloaded: {local_filename}")
        return local_filename
    except Exception as e:
        print(f"Failed to download {repo}: {e}")
        return None


def generate_masonry_markdown(repos: List[str]) -> str:
    """
    Generate Markdown with local SVG card references.

    Returns Markdown with local file references.
    """
    # Create cards directory if it doesn't exist
    cards_dir = "cards"
    os.makedirs(cards_dir, exist_ok=True)

    # Generate Markdown with local SVG references
    markdown_lines = []
    for repo in repos:
        # Download SVG file
        local_svg = download_svg(repo, cards_dir)

        if local_svg:
            repo_link = f"https://github.com/{repo}"
            # Generate Markdown: [![](cards/owner_repo.svg)](repo_link)
            markdown_lines.append(f'[![](cards/{local_svg})]({repo_link})')

    return '\n'.join(markdown_lines)


def main():
    """Main entry point - CLI mode."""
    if len(sys.argv) < 2:
        print("Usage: python simple_masonry.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: Markdown with local SVG references", file=sys.stderr)
        print("\nFeatures:", file=sys.stderr)
        print("  - No gh CLI required", file=sys.stderr)
        print("  - Downloads SVG files to cards/ directory", file=sys.stderr)
        print("  - Generates Markdown with local references", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]
    markdown = generate_masonry_markdown(repos)
    print(markdown)


if __name__ == "__main__":
    main()