# Database backend boundaries

Django models, migrations, QuerySets and transactions are the persistence API.
Guild features should continue using them directly. `config/database.py` contains
the database-specific connection settings and maintenance operations.

`DATABASE_BACKEND=sqlite` is the default and preserves existing data paths and
SQLite IMMEDIATE transactions. `DATABASE_PATH` overrides the database file;
otherwise local runs use `OPENIQ_DATA_DIR/db.sqlite3`, and Compose uses
`/data/db.sqlite3`. All three Compose services receive the same database settings.
No schema migration or data conversion is required for this abstraction.

## Adding a backend

1. Extend `DatabaseBackend`, providing the Django `engine` and a
   `configuration(data_dir, env)` method returning a Django database configuration.
2. Select it using its dotted class path in `DATABASE_BACKEND`, or add a short name
   to `BACKENDS`. Custom code must be installed in the application image.
3. For online backups, provide `snapshot_name`, `validate_snapshot(database)` and
   `snapshot(database, destination, timeout)`. Validation must fail before creating
   any output if the operation is unavailable. Write a consistent standalone
   snapshot to the supplied path and respect the timeout. The shared command
   handles staging, signing-key inclusion, checksums, private permissions,
   publication and retention.
4. Add backend configuration/capability tests and run real database integration
   tests for migrations, JSON fields, uniqueness, concurrent mutations and backups.

The base adapter rejects unsupported backup operations. Snapshot manifests now
include the Django engine; existing SQLite filenames and format remain unchanged.
Future restore code must treat old v1 manifests without an engine as SQLite and
reject incompatible engines rather than assuming every snapshot is a SQLite file.

## PostgreSQL preparation

`DATABASE_BACKEND=postgresql` (alias `postgres`) already builds Django PostgreSQL
settings from `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`,
`DATABASE_HOST`, `DATABASE_PORT`, and `DATABASE_SSLMODE`. Name and user are required.
SQLite options are never passed to PostgreSQL. Connections default to closing at
the end of a request (`CONN_MAX_AGE=0`).

This is configuration scaffolding, not a validated PostgreSQL deployment.
Before enabling it, add and lock a compatible psycopg driver, provision a test
database, run the integration matrix, implement PostgreSQL snapshot/restore
operations, and document data transfer from SQLite. The shipped image does not
include that driver or a PostgreSQL server. Selecting PostgreSQL does not migrate
existing SQLite data. The backup command explicitly rejects PostgreSQL until its
snapshot adapter exists.

## Mutation locking

`guilds.services.execute` runs inside `transaction.atomic` and updates the guild
revision before reading mutable domain records. The ORM UPDATE takes SQLite's
writer lock or a PostgreSQL row lock, held to transaction end. Keep that write
before domain reads; replacing it with an unlocked read risks lost updates.
Cross-guild operations still require concurrency review on each new database.

Reference: [Django database backend documentation](https://docs.djangoproject.com/en/5.2/ref/databases/).
