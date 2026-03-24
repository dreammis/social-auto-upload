#!/usr/bin/env bash

set -euo pipefail

account="creator"
video="videos/demo.mp4"
thumbnail="videos/demo.png"

sau kuaishou login --account "$account" --headed
sau kuaishou check --account "$account"

sau kuaishou upload-video \
  --account "$account" \
  --file "$video" \
  --title "Kuaishou video from bash" \
  --tags "cli,video" \
  --thumbnail "$thumbnail" \
  --headless

sau kuaishou upload-note \
  --account "$account" \
  --images "videos/1.png" "videos/2.png" "videos/3.png" \
  --note "Kuaishou note from bash" \
  --tags "cli,note" \
  --headless
