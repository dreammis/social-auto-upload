#!/usr/bin/env bash
# Restore B站 cookie from .bak backup.
# Use when sau bilibili upload-video fails with "cookie file missing" but .bak exists.
# Will not overwrite existing .json unless --force.
#
# Usage: restore_bilibili_cookie.sh --account <name> [--dry-run] [--force]

set -euo pipefail

ACCOUNT=""
DRY_RUN=0
FORCE=0
COOKIE_DIR="cookies"

usage() {
    cat <<'EOF'
Usage: restore_bilibili_cookie.sh --account <account_name> [--dry-run] [--force]

Restores cookies/bilibili_<account_name>.json from cookies/bilibili_<account_name>.json.bak.

Options:
  --account NAME   Bilibili account name (required)
  --dry-run        Show what would happen, don't modify anything
  --force          Overwrite existing .json if present

Examples:
  restore_bilibili_cookie.sh --account Pawly
  restore_bilibili_cookie.sh --account Pawly --dry-run
  restore_bilibili_cookie.sh --account Pawly --force

Next steps after restore:
  sau bilibili check --account Pawly   # verify cookie still valid
  sau bilibili login --account Pawly   # if invalid, re-login via QR code
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --account) ACCOUNT="$2"; shift 2;;
        --dry-run) DRY_RUN=1; shift;;
        --force) FORCE=1; shift;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown arg: $1" >&2; usage; exit 2;;
    esac
done

if [ -z "$ACCOUNT" ]; then
    echo "Error: --account is required" >&2
    usage
    exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COOKIE_JSON="${PROJECT_ROOT}/${COOKIE_DIR}/bilibili_${ACCOUNT}.json"
COOKIE_BAK="${PROJECT_ROOT}/${COOKIE_DIR}/bilibili_${ACCOUNT}.json.bak"

echo "[restore_bilibili_cookie] account: $ACCOUNT"
echo "[restore_bilibili_cookie] target: $COOKIE_JSON"
echo "[restore_bilibili_cookie] source: $COOKIE_BAK"

if [ ! -f "$COOKIE_BAK" ]; then
    echo "Error: no .bak file found at $COOKIE_BAK" >&2
    echo "  Nothing to restore. Re-login from scratch:" >&2
    echo "    sau bilibili login --account $ACCOUNT" >&2
    exit 1
fi

if [ -f "$COOKIE_JSON" ] && [ "$FORCE" != "1" ]; then
    echo "Error: cookie file already exists at $COOKIE_JSON" >&2
    echo "  Use --force to overwrite, or:" >&2
    echo "    mv $COOKIE_JSON ${COOKIE_JSON}.manual-backup.\$(date +%Y%m%d_%H%M%S)" >&2
    echo "    $0 --account $ACCOUNT" >&2
    exit 1
fi

# Always back up existing .bak before any operation
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_OF_BAK="${COOKIE_BAK}.${TIMESTAMP}"

if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY-RUN] Would backup $COOKIE_BAK → $BACKUP_OF_BAK"
    echo "[DRY-RUN] Would copy $COOKIE_BAK → $COOKIE_JSON"
    echo "[DRY-RUN] No changes made."
    exit 0
fi

echo "[restore_bilibili_cookie] Backing up .bak: $BACKUP_OF_BAK"
cp -p "$COOKIE_BAK" "$BACKUP_OF_BAK"

echo "[restore_bilibili_cookie] Restoring .bak → .json"
cp -p "$COOKIE_BAK" "$COOKIE_JSON"

echo ""
echo "✓ Cookie restored. Next steps:"
echo "  sau bilibili check --account $ACCOUNT     # verify cookie still valid"
echo "  sau bilibili login --account $ACCOUNT     # if invalid, re-login via QR"
echo ""
echo "Backup of original .bak preserved at: $BACKUP_OF_BAK"
