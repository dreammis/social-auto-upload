#!/usr/bin/env bash
set -euo pipefail

sau xueqiu login --account account_a
sau xueqiu check --account account_a
sau xueqiu upload-article --account account_a --title "雪球文章示例" --content-file articles/demo.md --declaration "不添加创作声明"
