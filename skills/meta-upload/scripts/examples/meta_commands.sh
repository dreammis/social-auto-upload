#!/usr/bin/env bash
set -euo pipefail

sau facebook-page login --account account_a
sau facebook-page check --account account_a
sau facebook-page upload-video --account account_a --page "示例 Page" --file videos/demo.mp4 --title "Facebook Page 视频示例" --desc "视频简介"
sau facebook-page upload-note --account account_a --page "示例 Page" --images images/1.jpg --title "Facebook Page 图文示例" --note "图文正文"
