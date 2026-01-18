#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator

A tool for generating CSS columns-based masonry/waterfall layout for GitHub project cards.
Features: fetch repo stats via gh CLI, sort by stars, generate HTML.

Usage:
    python scripts/generate_masonry.py owner/repo1 owner/repo2 ...

Output:
    HTML div with CSS columns for true masonry layout
"""

import sys
import subprocess
import json
from typing import List, Dict, Tuple


def fetch_repo_info(repo: str, max_retries: int = 2) -> Tuple[str, int, str]:
    """
    Fetch repository info using gh CLI with retry logic.

    Args:
        repo: Repository in owner/name format
        max_retries: Number of retries on failure (default: 2)

    Returns:
        (repo, stargazers, description)
    """
    cmd = [
        "gh", "repo", "view", repo,
        "--json", "stargazerCount,description,name",
        "--jq", '"\\(.name) | \\(.stargazerCount) | \\(.description)"'
    ]

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(" | ", 2)
                if len(parts) == 3:
                    name = parts[0]
                    stars = int(parts[1])
                    desc = parts[2]
                    return repo, stars, desc

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            if attempt < max_retries:
                continue  # Retry
            break

    # Fallback for private repos or errors after all retries
    return repo, 0, ""


def fetch_and_sort_repos(repos: List[str]) -> List[Tuple[str, int, str]]:
    """
    Fetch all repo info and sort by star count descending.

    Returns:
        List of (repo, stars, description) tuples sorted by stars
    """
    repo_data = []

    for repo in repos:
        repo_info = fetch_repo_info(repo)
        repo_data.append(repo_info)

    # Sort by star count descending
    repo_data.sort(key=lambda x: x[1], reverse=True)
    return repo_data


def generate_masonry_html(repos: List[str]) -> str:
    """
    Generate HTML with CSS columns for masonry layout.

    Fetches repo stats, sorts by stars, then outputs HTML.
    CSS columns automatically distribute cards and create waterfall effect.
    """
    # Fetch and sort repos
    sorted_repos = fetch_and_sort_repos(repos)

    lines = ['<div style="column-count: 2; column-gap: 8px;">']

    for repo, stars, desc in sorted_repos:
        url = f"https://gh-card.dev/repos/{repo}.svg"
        link = f"https://github.com/{repo}"
        lines.append(f'<a href="{link}"><img src="{url}" width="400"/></a>')

    lines.append('</div>')
    return '\n'.join(lines)


def main():
    """Main entry point - CLI mode."""
    if len(sys.argv) < 2:
        print("Usage: python generate_masonry.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: HTML div with CSS columns for masonry layout", file=sys.stderr)
        print("\nFeatures:", file=sys.stderr)
        print("  - Fetches star counts via gh CLI", file=sys.stderr)
        print("  - Sorts repos by stars (descending)", file=sys.stderr)
        print("  - Generates CSS columns masonry HTML", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]
    html = generate_masonry_html(repos)
    print(html)


if __name__ == "__main__":
    main()
