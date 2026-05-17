# Secrets — SOPS + age

Pantheon Trades secrets are encrypted at rest with **Mozilla SOPS** using
**age** keys. age is the modern, opinionated successor to PGP for
small-payload encryption (https://age-encryption.org).

Why SOPS + age:

- No paid vault dependency. Both tools are MIT-licensed, single static
  binaries, and run anywhere.
- Per-recipient encryption: rotating a single operator's access is a
  one-line `.sops.yaml` change + `sops updatekeys`.
- Encrypted files are valid YAML / dotenv — diffs stay reviewable
  because SOPS only encrypts *values*, not structure.

## Layout

```
.sops.yaml                       repo-wide encryption rules
.env.enc                         encrypted dotenv for compose
infra/secrets/<name>.yaml        encrypted YAML for k8s / kustomize
scripts/decrypt-env.sh           decrypts .env.enc -> .env locally
```

## One-time setup

1. Install SOPS and age:
   ```
   # macOS
   brew install sops age

   # Linux: grab static binaries from
   #   https://github.com/getsops/sops/releases
   #   https://github.com/FiloSottile/age/releases
   ```
2. Generate your operator key (private — never commit):
   ```
   age-keygen -o ~/.config/sops/age/keys.txt
   chmod 600 ~/.config/sops/age/keys.txt
   ```
   The file prints your **public** key (`age1...`). Send only the
   public key to whoever owns `.sops.yaml`.
3. The owner appends your public key to every `age:` entry in
   `.sops.yaml`, then re-keys existing payloads:
   ```
   sops updatekeys .env.enc
   sops updatekeys infra/secrets/*.yaml
   ```
4. Pull the latest, and `scripts/decrypt-env.sh` should now work.

## Encrypting a new value

```
# create or edit .env.enc — SOPS opens an editor on the cleartext.
sops .env.enc

# inline edit:
echo "NEW_SECRET=value" | sops --input-type dotenv --output-type dotenv -e /dev/stdin >> .env.enc
```

## Decrypting at compose-up

```
./scripts/decrypt-env.sh
docker compose --env-file .env up -d
```

The decrypt script refuses to run without an age key file present so a
fresh clone fails fast rather than silently shipping a half-configured
stack.

## Rotating a key

A leaked operator key invalidates the data key wrap, not the data
itself. Revoke:

1. Remove the leaked public key from every `age:` entry in `.sops.yaml`.
2. `sops updatekeys .env.enc` (and every other tracked encrypted
   file). This re-wraps each data key against the remaining recipients.
3. Commit `.sops.yaml` + the re-wrapped files together.

## What MUST stay outside SOPS

- The deployer wallet's `PRIVATE_KEY` — that one belongs in a
  hardware-backed signer (Frame, Ledger, Gnosis Safe) in production.
- `ANTHROPIC_API_KEY` for CI — use the CI provider's own secret store
  (GitHub Actions secrets, etc.) and do not duplicate into SOPS.

## CI / Server

On a deployment server, place `keys.txt` at
`/etc/sops/age/keys.txt`, set `SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt`,
and run `scripts/decrypt-env.sh` as part of the deploy step. Never log
the decrypted env file.
