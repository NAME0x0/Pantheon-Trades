# Backup Service

Hourly snapshot of Postgres + Redis, written to `./backups` on the host.

## What it does

Every `BACKUP_INTERVAL_SECONDS` (default 3600 = 1 hour):

1. `pg_dump -F c -Z 6 -b` → `backups/pg-pantheon-<UTC>.dump`
2. `redis-cli BGSAVE`, wait for LASTSAVE to tick, then tar
   `dump.rdb` (and `appendonly.aof` if present) → `backups/redis-<UTC>.tar.gz`
3. Prune any backup file older than `BACKUP_RETENTION_DAYS` (default 14d)

Logs to stdout so `docker compose logs backup` is the single source of
truth for whether backups have been running.

## Restoring

Postgres:

```bash
gunzip -k backups/pg-pantheon-20260516T120000Z.dump
docker compose exec -T postgres pg_restore \
    -U pantheon -d pantheon -c --if-exists \
    < backups/pg-pantheon-20260516T120000Z.dump
```

Redis (point-in-time, AOF preferred):

```bash
docker compose down redis
tar -xzf backups/redis-20260516T120000Z.tar.gz -C /var/lib/docker/volumes/pantheon-trades_pantheon-redis/_data/
docker compose up -d redis
```

## Off-host shipping

The service writes to `/backups` inside the container, mounted from
`./backups` on the host. Wire `./backups` to S3 / Backblaze / etc.
with restic / rclone for off-host retention — out of scope for this
service.

## Tuning

| Env var                     | Default | Notes                          |
|-----------------------------|---------|--------------------------------|
| `BACKUP_INTERVAL_SECONDS`   | `3600`  | Loop sleep between runs        |
| `BACKUP_RETENTION_DAYS`     | `14`    | Local prune threshold          |
| `PG_HOST` / `PG_PORT`       | postgres:5432 | Override for non-compose    |
| `REDIS_HOST` / `REDIS_PORT` | redis:6379 | Override for non-compose       |

A failed backup logs to stderr and exits non-zero from the inner
script; the outer entrypoint loop continues so a transient failure
does not stop future attempts.
