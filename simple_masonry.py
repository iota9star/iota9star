#!/usr/bin/env python3
"""
Simple masonry layout generator using GitHub API
"""
import requests
import re
import os
from pathlib import Path

def get_stars(repo):
    """Get star count for a repo using GitHub API"""
    owner, name = repo.split('/')
    url = f"https://api.github.com/repos/{owner}/{name}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('stargazers_count', 0)
    except Exception as e:
        print(f"Error fetching {repo}: {e}")
    return 0

def get_repo_description(repo):
    """Get repo description using GitHub API"""
    owner, name = repo.split('/')
    url = f"https://api.github.com/repos/{owner}/{name}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('description', 'No description available.')
    except Exception as e:
        print(f"Error fetching description for {repo}: {e}")
    return 'No description available.'

def get_repo_language(repo):
    """Get repo primary language using GitHub API"""
    owner, name = repo.split('/')
    url = f"https://api.github.com/repos/{owner}/{name}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('language', 'Unknown')
    except Exception as e:
        print(f"Error fetching language for {repo}: {e}")
    return 'Unknown'

def generate_svg_card(repo, stars, description, language):
    """Generate an SVG card for a repo"""
    # Create cards directory if it doesn't exist
    cards_dir = Path("cards")
    cards_dir.mkdir(exist_ok=True)

    # Sanitize repo name for filename
    safe_name = repo.replace('/', '_')
    filename = cards_dir / f"{safe_name}.svg"

    # Truncate description if too long
    display_desc = description[:50] + "..." if len(description) > 50 else description

    # Generate SVG content with modern gradient card design
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="8" flood-opacity="0.3"/>
    </filter>
  </defs>

  <!-- Card Background -->
  <rect width="400" height="200" rx="16" fill="url(#grad)" filter="url(#shadow)"/>

  <!-- Content -->
  <text x="200" y="60" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="white" text-anchor="middle">{repo}</text>
  <text x="200" y="90" font-family="Arial, sans-serif" font-size="14" fill="rgba(255,255,255,0.9)" text-anchor="middle">{display_desc}</text>
  <text x="200" y="120" font-family="Arial, sans-serif" font-size="12" fill="rgba(255,255,255,0.7)" text-anchor="middle">{language}</text>
  <text x="200" y="150" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="white" text-anchor="middle">⭐ {stars:,}</text>
</svg>'''

    # Write SVG file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    return filename

def main():
    """Main function to generate masonry layout"""
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

    print("🔄 Fetching repo data...")

    # Get star counts and metadata for all repos
    repo_data = []
    for repo in repos:
        print(f"  Fetching {repo}...")
        stars = get_stars(repo)
        description = get_repo_description(repo)
        language = get_repo_language(repo)
        repo_data.append({
            'repo': repo,
            'stars': stars,
            'description': description,
            'language': language
        })

    # Sort by stars descending
    repo_data.sort(key=lambda x: x['stars'], reverse=True)

    print(f"\n✅ Generating SVG cards for {len(repo_data)} repos...")

    # Generate SVG cards
    markdown_lines = []
    for data in repo_data:
        svg_path = generate_svg_card(data['repo'], data['stars'], data['description'], data['language'])
        safe_name = data['repo'].replace('/', '_')
        markdown_lines.append(f'[![](cards/{safe_name}.svg)](https://github.com/{data["repo"]})')

    # Output Markdown
    print("\n" + "="*60)
    print("📝 MARKDOWN OUTPUT (copy this):")
    print("="*60)
    for line in markdown_lines:
        print(line)
    print("="*60)
    print(f"\n✅ Done! SVG cards saved to 'cards/' directory")
    print(f"📊 Generated {len(repo_data)} cards")

if __name__ == "__main__":
    main()
