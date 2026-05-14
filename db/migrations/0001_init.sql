-- 0001_init: full initial schema.
-- Identical to db/schema.sql — kept here so plain psql-based migration
-- ordering still works for environments that do not run Alembic.
\i db/schema.sql
