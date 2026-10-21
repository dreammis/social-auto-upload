#!/usr/bin/env bash
set -euo pipefail

sau facebook login --account account_a
sau facebook check --account account_a
sau facebook upload-video --account account_a --file videos/demo.mp4 --title "Facebook 视频示例" --desc "视频简介" --tags life,share
sau facebook upload-note --account account_a --images images/1.jpg images/2.jpg --title "Facebook 图文示例" --note "图文正文"
