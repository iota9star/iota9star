#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator with Local SVG Files

Generates Markdown with local SVG card files.
Downloads SVG files from gh-card.dev to cards/ directory.

Usage:
    python scripts/generate_masonry_local.py owner/repo1 owner/repo2 ...

Output:
    Markdown with local SVG references
"""

import sys
import subprocess
import urllib.request
import os
from typing import List, Tuple


def fetch_repo_stars(repo: str, max_retries: int = 2) -> Tuple[str, int]:
    """Fetch repository star count using gh CLI with retry logic."""
    cmd = [
        "gh", "repo", "view", repo,
        "--json", "stargazerCount",
        "--jq", ".stargazerCount"
    ]

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return repo, int(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            if attempt < max_retries:
                continue
            break

    return repo, 0


def fetch_and_sort_repos(repos: List[str]) -> List[Tuple[str, int]]:
    """Fetch all repo stars and sort by star count descending."""
    repo_data = []
    for repo in repos:
        repo_info = fetch_repo_stars(repo)
        repo_data.append(repo_info)
        print(f"Fetched stars for {repo}: {repo_info[1]}")

    repo_data.sort(key=lambda x: x[1], reverse=True)
    return repo_data


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

    # Fetch and sort repos by stars
    sorted_repos = fetch_and_sort_repos(repos)

    # Generate Markdown with local SVG references
    markdown_lines = []
    for repo, stars in sorted_repos:
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
        print("Usage: python generate_masonry_local.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: Markdown with local SVG references", file=sys.stderr)
        print("\nFeatures:", file=sys.stderr)
        print("  - Fetches star counts via gh CLI", file=sys.stderr)
        print("  - Sorts repos by stars (descending)", file=sys.stderr)
        print("  - Downloads SVG files to cards/ directory", file=sys.stderr)
        print("  - Generates Markdown with local references", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]
    markdown = generate_masonry_markdown(repos)
    print(markdown)


if __name__ == "__main__":
    main()