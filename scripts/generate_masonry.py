#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator

Generates HTML table with project cards using gh-card.dev URLs.
No local files needed - GitHub renders gh-card.dev images directly.

Usage:
    python scripts/generate_masonry.py owner/repo1 owner/repo2 ...

Output:
    HTML table with 2-column layout
"""

import sys
import subprocess
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
    repo_data.sort(key=lambda x: x[1], reverse=True)
    return repo_data


def generate_masonry_html(repos: List[str]) -> str:
    """
    Generate HTML table with gh-card.dev URLs.

    Returns HTML table with gh-card.dev image references.
    """
    # Fetch and sort repos
    sorted_repos = fetch_and_sort_repos(repos)

    # Prepare HTML with gh-card.dev URLs
    cards_html = []
    for repo, stars in sorted_repos:
        card_url = f"https://gh-card.dev/repos/{repo}.svg"
        repo_link = f"https://github.com/{repo}"

        # Generate HTML: <a href="repo_link"><img src="gh-card_url" /></a>
        cards_html.append(f'<a href="{repo_link}"><img src="{card_url}" alt="{repo}" /></a>')

    # Create 2-column table layout
    lines = ['<table>', '<tr>']
    for i, html in enumerate(cards_html):
        if i > 0 and i % 2 == 0:
            lines.append('</tr><tr>')
        lines.append(f'<td align="center">{html}</td>')
    lines.append('</tr>')

    # Handle odd number of cards
    if len(cards_html) % 2 != 0:
        lines.insert(-1, '<td></td>')

    lines.append('</table>')
    return '\n'.join(lines)


def main():
    """Main entry point - CLI mode."""
    if len(sys.argv) < 2:
        print("Usage: python generate_masonry.py owner/repo1 owner/repo2 ...", file=sys.stderr)
        print("\nOutput: HTML table with 2-column layout", file=sys.stderr)
        print("\nFeatures:", file=sys.stderr)
        print("  - Fetches star counts via gh CLI", file=sys.stderr)
        print("  - Sorts repos by stars (descending)", file=sys.stderr)
        print("  - Uses gh-card.dev URLs (no local files)", file=sys.stderr)
        print("  - Generates 2-column table layout", file=sys.stderr)
        sys.exit(1)

    repos = sys.argv[1:]
    html = generate_masonry_html(repos)
    print(html)


if __name__ == "__main__":
    main()
