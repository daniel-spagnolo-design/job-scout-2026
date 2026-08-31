#!/usr/bin/env bash
# Copies jobs-log.md into an Obsidian vault as a normal note.
#
# The weekly scan runs in GitHub Actions, so the fresh log lives on GitHub — this
# pulls first, then copies. The vault is in iCloud, where symlinks don't sync
# reliably, so this writes a real file (atomically, via tmp + mv).
#
# Run manually any time, or on a schedule via the LaunchAgent.
#
# NOTE ON THE SCHEDULED COPY: macOS TCC blocks LaunchAgents from reading ~/Documents,
# so the agent can't use the working repo. It instead runs an installed copy of this
# script against a mirror clone under ~/Library/Application Support/job-scout-sync/,
# with JOB_SCOUT_REPO pointing at that mirror. Re-run scripts/install_obsidian_sync.sh
# after editing this file to refresh the installed copy.
set -uo pipefail

# Default to the repo this script lives in; the LaunchAgent overrides via env.
REPO="${JOB_SCOUT_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VAULT="${JOB_SCOUT_VAULT:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/career}"
NOTE="${JOB_SCOUT_NOTE:-Job Scout.md}"

SRC="$REPO/jobs-log.md"
DEST="$VAULT/$NOTE"

[ -d "$VAULT" ] || { echo "Vault not found: $VAULT" >&2; exit 1; }

# Fetch the latest run's results. Non-fatal: if offline or the tree is dirty we
# just sync whatever is already checked out.
git -C "$REPO" pull --ff-only --quiet 2>/dev/null \
  || echo "note: git pull skipped/failed — syncing local copy"

[ -f "$SRC" ] || { echo "Source not found: $SRC" >&2; exit 1; }

# Date of the last commit that touched the log — stable, so an unchanged log
# produces an identical note and we can skip rewriting it (avoids iCloud churn).
updated="$(git -C "$REPO" log -1 --format=%cs -- jobs-log.md 2>/dev/null)"
[ -n "$updated" ] || updated="$(date '+%Y-%m-%d')"

tmp="$(mktemp)"
{
  echo "---"
  echo "source: job-scout-2026/jobs-log.md"
  echo "updated: $updated"
  echo "tags: [job-search, job-scout]"
  echo "---"
  echo
  echo "> [!info] Auto-synced from the \`job-scout-2026\` repo. Edits here get overwritten — change the source, not this note."
  echo
  cat "$SRC"
} > "$tmp"

if [ -f "$DEST" ] && cmp -s "$tmp" "$DEST"; then
  rm -f "$tmp"
  echo "No change — $NOTE already up to date (log last updated $updated)."
  exit 0
fi

mv "$tmp" "$DEST"
echo "Synced → $DEST (log last updated $updated)"
