#!/usr/bin/env sh
# Pantheon backup script. Runs hourly inside the `backup` compose
# service. Snapshots Postgres via pg_dump (custom format) and triggers
# a Redis BGSAVE; both artifacts land in /backups with a UTC timestamp.
#
# Retention is enforced by age (BACKUP_RETENTION_DAYS, default 14).
# Failure to back up MUST exit non-zero so the cron loop logs it loud.

set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-pantheon}"
PG_DB="${PG_DB:-pantheon}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

mkdir -p "${BACKUP_DIR}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

# ─── Postgres ─────────────────────────────────────────────────────
PG_OUT="${BACKUP_DIR}/pg-${PG_DB}-${TS}.dump"
echo "[backup ${TS}] dumping postgres -> ${PG_OUT}"
PGPASSWORD="${PGPASSWORD:-pantheon}" pg_dump \
    -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" \
    -F c -Z 6 -b -v \
    -f "${PG_OUT}" "${PG_DB}"

# ─── Redis ─────────────────────────────────────────────────────────
# BGSAVE asks the running redis to fork-and-snapshot. We poll until
# LASTSAVE timestamp changes, then copy the resulting dump.rdb out.
echo "[backup ${TS}] triggering redis bgsave"
PREV_SAVE="$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" LASTSAVE)"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" BGSAVE >/dev/null

i=0
while [ "$i" -lt 60 ]; do
    sleep 1
    NEW_SAVE="$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" LASTSAVE)"
    if [ "${NEW_SAVE}" != "${PREV_SAVE}" ]; then
        break
    fi
    i=$((i + 1))
done
if [ "${NEW_SAVE}" = "${PREV_SAVE}" ]; then
    echo "[backup ${TS}] redis BGSAVE never completed; aborting" >&2
    exit 1
fi

# Redis sets the dump.rdb path via CONFIG. Default in alpine image is
# /data/dump.rdb. We dump to a tar so it travels with anything else
# Redis has written there (appendonly.aof).
REDIS_OUT="${BACKUP_DIR}/redis-${TS}.tar.gz"
echo "[backup ${TS}] archiving redis dump -> ${REDIS_OUT}"
tar -czf "${REDIS_OUT}" -C /redis-data dump.rdb 2>/dev/null \
    || tar -czf "${REDIS_OUT}" -C /redis-data appendonly.aof dump.rdb 2>/dev/null \
    || (echo "[backup ${TS}] redis dump file not found" >&2 && exit 1)

# ─── Retention ─────────────────────────────────────────────────────
echo "[backup ${TS}] pruning artifacts older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -type f -mtime "+${RETENTION_DAYS}" \
    \( -name 'pg-*.dump' -o -name 'redis-*.tar.gz' \) -print -delete

echo "[backup ${TS}] done"
