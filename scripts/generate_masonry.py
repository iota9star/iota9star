#!/usr/bin/env python3
"""
GitHub Profile Masonry Layout Generator

Generates README.md with masonry/waterfall layout for GitHub project cards.
Uses only Python standard library - zero external dependencies.
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict


class MasonryGenerator:
    """Generates masonry layout for GitHub profile cards."""

    def __init__(self, profile_path: str = "profile.md", output_path: str = "README.md"):
        self.profile_path = Path(profile_path)
        self.output_path = Path(output_path)
        self.temp_dir = Path("temp")
        self.repos: List[Dict] = []

    def read_profile(self) -> str:
        """Read profile.md content before REPOS section."""
        content = self.profile_path.read_text(encoding="utf-8")
        # Split at REPOS comment
        parts = content.split("<!-- REPOS")
        return parts[0] if parts else content

    def extract_repos(self) -> List[str]:
        """Extract repo URLs from profile.md REPOS section."""
        content = self.profile_path.read_text(encoding="utf-8")

        # Extract URLs from REPOS comment section
        repos_match = re.search(
            r"<!-- REPOS\n(.*?)REPOS -->",
            content,
            re.DOTALL
        )

        if not repos_match:
            return []

        repos_text = repos_match.group(1)
        # Extract github.com URLs
        urls = re.findall(r"https://github\.com/([^/\s]+/[^/\s]+)", repos_text)

        return list(set(urls))  # Deduplicate

    def download_svg(self, repo: str) -> Path:
        """Download gh-card SVG for a repo."""
        owner, name = repo.split("/")
        filename = f"{owner}-{name}.svg"
        filepath = self.temp_dir / filename
        url = f"https://gh-card.dev/repos/{repo}.svg"

        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"Downloaded: {repo}")
            return filepath
        except urllib.error.URLError as e:
            print(f"Failed to download {repo}: {e}")
            return None

    def parse_svg_size(self, filepath: Path) -> Tuple[int, int]:
        """Parse width and height from SVG file."""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # Try width/height attributes first
            width = root.get("width")
            height = root.get("height")

            if width and height:
                # Remove 'px' suffix if present
                width = int(width.rstrip("px"))
                height = int(height.rstrip("px"))
                return width, height

            # Try viewBox attribute
            viewbox = root.get("viewBox")
            if viewbox:
                # viewBox="0 0 width height"
                _, _, width, height = map(float, viewbox.split())
                return int(width), int(height)

            # Default fallback
            return 400, 200

        except Exception as e:
            print(f"Failed to parse {filepath}: {e}")
            return 400, 200

    def calculate_masonry_layout(self, cards: List[Dict]) -> Tuple[int, List[Dict]]:
        """
        Calculate masonry waterfall layout positions.

        Returns: (total_height, cards_with_positions)
        """
        gap = 8  # Gap between cards in pixels
        col_width = 49.5  # Percentage width for each column

        left_y = 0
        right_y = 0

        for card in cards:
            height = card["height"]

            if left_y <= right_y:
                # Place in left column
                card["x"] = 0
                card["y"] = left_y
                left_y += height + gap
            else:
                # Place in right column
                card["x"] = 50.5
                card["y"] = right_y
                right_y += height + gap

        total_height = max(left_y, right_y)
        return total_height, cards

    def generate_svg_content(self, cards: List[Dict], total_height: int) -> str:
        """Generate SVG element with masonry layout."""
        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="{}">'.format(total_height)]

        for card in cards:
            repo = card["repo"]
            owner, name = repo.split("/")
            x = card["x"]
            y = card["y"]
            height = card["height"]

            # Format x coordinate: 0 for left, 50.5% for right
            x_str = "0" if x == 0 else f"{x}%"

            svg_parts.append(f'''  <a href="https://github.com/{repo}">
    <image x="{x_str}" y="{y}" width="49.5%" height="{height}" href="https://gh-card.dev/repos/{repo}.svg"/>
  </a>''')

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def generate_readme(self, profile_content: str, svg_content: str) -> str:
        """Generate complete README.md content."""
        # TODO: Enhance with more sections
        # For now, simple structure

        lines = [
            profile_content.strip(),
            "",
            "## 🔥 Featured Projects",
            "",
            svg_content,
            "",
            "<!-- Auto-generated by scripts/generate_masonry.py -->"
        ]

        return "\n".join(lines)

    def run(self):
        """Main execution flow."""
        print("🔨 Starting masonry layout generation...")

        # Create temp directory
        self.temp_dir.mkdir(exist_ok=True)

        # Read profile
        print("📖 Reading profile.md...")
        profile_content = self.read_profile()

        # Extract repos
        print("🔍 Extracting repositories...")
        repos = self.extract_repos()
        print(f"Found {len(repos)} repositories")

        if not repos:
            print("⚠️ No repositories found!")
            return

        # Download SVGs and parse sizes
        print("📥 Downloading GitHub cards...")
        cards = []
        for repo in repos:
            filepath = self.download_svg(repo)
            if filepath:
                width, height = self.parse_svg_size(filepath)
                cards.append({
                    "repo": repo,
                    "width": width,
                    "height": height,
                    "filepath": filepath
                })

        # Sort by popularity (could add star count later)
        # For now, keep original order

        # Calculate masonry layout
        print("🧱 Calculating masonry layout...")
        total_height, cards_with_pos = self.calculate_masonry_layout(cards)

        # Generate SVG content
        print("🎨 Generating SVG...")
        svg_content = self.generate_svg_content(cards_with_pos, total_height)

        # Generate README
        print("📝 Generating README.md...")
        readme_content = self.generate_readme(profile_content, svg_content)

        # Write output
        self.output_path.write_text(readme_content, encoding="utf-8")

        print(f"✅ Done! Generated {self.output_path}")
        print(f"   Total height: {total_height}px, {len(cards)} cards")


def main():
    """Entry point."""
    generator = MasonryGenerator()
    generator.run()


if __name__ == "__main__":
    main()
