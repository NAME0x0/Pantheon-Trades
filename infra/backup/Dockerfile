# Lightweight image with pg_dump + redis-cli + tar.
FROM postgres:16-alpine

RUN apk add --no-cache redis tar

COPY backup.sh /usr/local/bin/backup.sh
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/backup.sh /usr/local/bin/entrypoint.sh

# Backup artifacts land in /backups (host-mounted via compose).
VOLUME ["/backups"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
