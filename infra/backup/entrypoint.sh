#!/usr/bin/env sh
# Runs backup.sh every BACKUP_INTERVAL_SECONDS (default 3600).
# Logs to stdout so docker compose captures it.

set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-3600}"

echo "[backup-loop] interval=${INTERVAL}s retention=${BACKUP_RETENTION_DAYS:-14}d"

# Run once at startup so we don't wait for the first interval.
/usr/local/bin/backup.sh || echo "[backup-loop] first run failed"

while true; do
    sleep "${INTERVAL}"
    /usr/local/bin/backup.sh || echo "[backup-loop] run failed at $(date -u +%FT%TZ)"
done
