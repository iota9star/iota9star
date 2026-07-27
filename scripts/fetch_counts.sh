#!/usr/bin/env bash
#
# Fetch star + fork counts for every profile repo via the GitHub REST API
# using only curl + jq (no `gh` auth, no Python). Handy in sandboxes where
# the gh CLI or network-bound Python is unavailable.
#
# Usage:  bash scripts/fetch_counts.sh
# Output: TSV lines "<stars>\t<forks>\t<repo>", already sorted by stars desc.
#
set -euo pipefail

REPOS=(
  fluttercandies/fjs fluttercandies/hora fluttercandies/dpad
  fluttercandies/resx fluttercandies/f_limit fluttercandies/json_dart
  fluttercandies/env2dart fluttercandies/flexbox_layout
  fluttercandies/dotrix fluttercandies/dash_router
  fluttercandies/vcard_dart fluttercandies/svgo
  void-signals/void_signals iota9star/mikan_flutter
  iota9star/sakura-dmhy iota9star/kisssub
)

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

for repo in "${REPOS[@]}"; do
  curl -fsS -m 12 -H "User-Agent: iota9star-profile" \
    "https://api.github.com/repos/${repo}" \
    | jq -r '[.stargazers_count, .forks_count, .full_name] | @tsv' >> "$tmp" || true
done

sort -t$'\t' -k1,1nr "$tmp"
