#!/usr/bin/env bash
# Installs (or refreshes) the daily Obsidian sync.
#
# Why the indirection: macOS TCC blocks LaunchAgents from reading ~/Documents, where
# the working repo lives — a scheduled job there fails with "Operation not permitted"
# (exit 126). The iCloud vault itself IS writable by an agent, so the fix is to keep
# everything the agent touches outside ~/Documents:
#
#   ~/Library/Application Support/job-scout-sync/
#       repo/                  mirror clone, pulled from GitHub each run
#       sync_to_obsidian.sh    installed copy of scripts/sync_to_obsidian.sh
#
# The agent runs the installed copy against the mirror. Your working repo is untouched.
# Re-run this script after editing sync_to_obsidian.sh to refresh the installed copy.
set -euo pipefail

REPO_URL="https://github.com/daniel-spagnolo-design/job-scout-2026.git"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_DIR="$HOME/Library/Application Support/job-scout-sync"
MIRROR="$SYNC_DIR/repo"
LABEL="com.daniel-spagnolo.job-scout-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$SYNC_DIR" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

# 1. Mirror clone (outside ~/Documents so the agent can read it)
if [ -d "$MIRROR/.git" ]; then
  echo "Mirror exists — fetching."
  git -C "$MIRROR" pull --ff-only --quiet || echo "  (pull failed; leaving mirror as-is)"
else
  echo "Cloning mirror → $MIRROR"
  git clone --quiet "$REPO_URL" "$MIRROR"
fi

# 2. Installed copy of the sync script
cp "$SRC_DIR/sync_to_obsidian.sh" "$SYNC_DIR/sync_to_obsidian.sh"
chmod +x "$SYNC_DIR/sync_to_obsidian.sh"

# 3. LaunchAgent — daily at 09:00. Daily (not weekly) so a Mac that was asleep on
#    Monday still syncs: launchd runs a missed calendar job at next wake.
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$LABEL</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/bash</string>
		<string>$SYNC_DIR/sync_to_obsidian.sh</string>
	</array>
	<key>EnvironmentVariables</key>
	<dict>
		<key>JOB_SCOUT_REPO</key>
		<string>$MIRROR</string>
	</dict>
	<key>StartCalendarInterval</key>
	<dict>
		<key>Hour</key><integer>9</integer>
		<key>Minute</key><integer>0</integer>
	</dict>
	<key>RunAtLoad</key>
	<false/>
	<key>StandardOutPath</key>
	<string>$HOME/Library/Logs/job-scout-sync.log</string>
	<key>StandardErrorPath</key>
	<string>$HOME/Library/Logs/job-scout-sync.log</string>
</dict>
</plist>
PLIST_EOF

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"

echo "Installed. Agent '$LABEL' runs daily at 09:00."
echo "Test now:  launchctl kickstart -k gui/\$UID/$LABEL"
echo "Log:       ~/Library/Logs/job-scout-sync.log"
echo "Uninstall: launchctl bootout gui/\$UID/$LABEL && rm '$PLIST'"
