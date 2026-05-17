# Pantheon API — Database Migrations

Alembic-driven, async-aware. Reads `DATABASE_URL` from the same
config object FastAPI uses (`pantheon_api.config.settings`).

## Common operations

Run from `apps/api/`:

```bash
# Generate a migration that diffs against current models.py
uv run alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one revision
uv run alembic downgrade -1

# Inspect current revision applied to the DB
uv run alembic current

# Show full upgrade history
uv run alembic history --verbose

# Emit SQL only (offline mode — no DB connection needed)
uv run alembic upgrade head --sql > schema.sql
```

## Workflow

1. Edit `src/pantheon_api/models.py` — add / drop / alter columns.
2. `alembic revision --autogenerate -m "..."` — review the generated
   file under `migrations/versions/`.
3. Always sanity-check autogen output. Alembic catches column adds /
   drops cleanly but misses:
   - Enum renames (does a full drop/create)
   - Server-default changes without `compare_server_default=True`
   - Table renames (interprets as drop + create)
4. Commit the migration file alongside the models change.
5. CI runs `alembic upgrade head` against the test database before
   pytest fires.

## Conventions

- One commit per migration. Never edit a merged migration in place —
  add a new revision that corrects it.
- File template: `YYYYMMDD_HHMM_<slug>.py` (configured in `alembic.ini`).
- Every migration is **runnable in both directions**. If a downgrade
  is genuinely destructive, raise in `downgrade()` and document why.
- Migrations must not import service code outside `pantheon_api`.
