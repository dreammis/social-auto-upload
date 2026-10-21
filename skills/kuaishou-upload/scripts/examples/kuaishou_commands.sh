#!/usr/bin/env bash

set -euo pipefail

# account_name is user-defined. One account_name maps to one account file.
# You can prepare multiple account names and run them in parallel.
account="account_a"
video="videos/demo.mp4"
thumbnail="videos/demo.png"

sau kuaishou login --account "$account"
sau kuaishou check --account "$account"

sau kuaishou upload-video \
  --account "$account" \
  --file "$video" \
  --title "Kuaishou video from bash" \
  --desc "Kuaishou video description from bash" \
  --tags "cli,video" \
  --thumbnail "$thumbnail" \
  --headless

sau kuaishou upload-note \
  --account "$account" \
  --images "videos/1.png" "videos/2.png" "videos/3.png" \
  --title "Kuaishou note title from bash" \
  --note "Kuaishou note from bash" \
  --tags "cli,note" \
  --headless
