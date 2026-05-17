#!/usr/bin/env sh
# Decrypts .env.enc into .env using SOPS + the active age private key.
# Run this before `docker compose up`. Idempotent: safe to re-run.

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${REPO_ROOT}/.env.enc"
DEST="${REPO_ROOT}/.env"

if ! command -v sops >/dev/null 2>&1; then
    echo "sops not found. Install: brew install sops, or"
    echo "  https://github.com/getsops/sops/releases" >&2
    exit 1
fi
if [ ! -f "${SRC}" ]; then
    echo "no encrypted env at ${SRC} — see infra/secrets/README.md" >&2
    exit 1
fi
if [ -z "${SOPS_AGE_KEY_FILE:-}" ] && [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
    echo "no age key file: set SOPS_AGE_KEY_FILE or place keys.txt at" >&2
    echo "  \$HOME/.config/sops/age/keys.txt — see infra/secrets/README.md" >&2
    exit 1
fi

sops --decrypt "${SRC}" > "${DEST}.tmp"
mv "${DEST}.tmp" "${DEST}"
chmod 600 "${DEST}"
echo "decrypted $(basename "${SRC}") -> $(basename "${DEST}")"
