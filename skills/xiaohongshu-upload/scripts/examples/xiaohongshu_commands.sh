#!/usr/bin/env bash

set -euo pipefail

# account_name is user-defined. One account_name maps to one account file.
# You can prepare multiple account names and run them in parallel.
account="account_a"
video="videos/demo.mp4"
thumbnail="videos/demo.png"

sau xiaohongshu login --account "$account" --headless
sau xiaohongshu check --account "$account"

sau xiaohongshu upload-video \
  --account "$account" \
  --file "$video" \
  --title "Xiaohongshu video from bash" \
  --desc "Xiaohongshu video description from bash" \
  --tags "cli,video" \
  --thumbnail "$thumbnail" \
  --headless

sau xiaohongshu upload-note \
  --account "$account" \
  --images "videos/1.png" "videos/2.png" \
  --title "Xiaohongshu note title from bash" \
  --note "Xiaohongshu note from bash" \
  --tags "cli,note" \
  --headless
