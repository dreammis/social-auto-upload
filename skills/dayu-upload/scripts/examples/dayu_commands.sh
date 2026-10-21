#!/usr/bin/env bash
set -euo pipefail

sau dayu login --account account_a
sau dayu check --account account_a
sau dayu upload-video --account account_a --file videos/demo.mp4 --title "大鱼号视频示例" --category "科技" --source "无需标注" --thumbnail videos/demo.png
sau dayu upload-article --account account_a --title "大鱼号文章示例" --content-file articles/demo.md --source "无需标注"
