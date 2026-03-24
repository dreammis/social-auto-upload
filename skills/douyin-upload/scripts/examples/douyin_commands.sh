#!/usr/bin/env bash

set -euo pipefail

account="creator"
video="videos/demo.mp4"
thumbnail="videos/demo.png"

sau douyin login --account "$account" --headless
sau douyin check --account "$account"

sau douyin upload-video \
  --account "$account" \
  --file "$video" \
  --title "Douyin video from bash" \
  --tags "cli,video" \
  --thumbnail "$thumbnail" \
  --headless

sau douyin upload-note \
  --account "$account" \
  --images "videos/1.png" "videos/2.png" \
  --note "Douyin note from bash" \
  --tags "cli,note" \
  --headless
