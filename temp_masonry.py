#!/usr/bin/env python3
repos = [
    'fluttercandies/fjs', 'fluttercandies/hora', 'fluttercandies/dpad',
    'fluttercandies/resx', 'fluttercandies/f_limit', 'fluttercandies/json_dart',
    'fluttercandies/env2dart', 'fluttercandies/flexbox_layout', 'fluttercandies/dotrix',
    'fluttercandies/dash_router', 'fluttercandies/vcard_dart', 'fluttercandies/svgo',
    'void-signals/void_signals', 'iota9star/mikan_flutter', 'iota9star/sakura-dmhy',
    'iota9star/kisssub'
]

# Generate HTML with gh-card.dev URLs
cards_html = []
for repo in repos:
    card_url = f'https://gh-card.dev/repos/{repo}.svg'
    repo_link = f'https://github.com/{repo}'
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
print('\n'.join(lines))
