#!/usr/bin/env bash
set -euo pipefail

sau facebook login --account account_a
sau facebook check --account account_a
sau facebook upload-video --account account_a --file videos/demo.mp4 --title VideoTitle --desc Description --tags life,share
sau facebook upload-note --account account_a --images images/1.jpg images/2.jpg --title NoteTitle --note Text
