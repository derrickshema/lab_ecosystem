# Local infrastructure

One PostgreSQL server shared by every app during local development. Each app has its own database and its own user, and a user can only connect to its own database.

| App | Database | User / password |
|---|---|---|
| EHR | `ehr_db` | `ehr_user` / `ehr_123` |
| LabLenz | `lablenz_db` | `lablenz_user` / `lablenz_123` |
| Identity | `identity_db` | `identity_user` / `identity_123` |

Server admin: user `postgres`, password from `infrastructure/.env`.

## First-time setup

```sh
cd infrastructure
cp .env.example .env    # then set POSTGRES_PASSWORD in .env
```

`.env` is gitignored, so the admin password never reaches the repo. Compose reads it automatically and fills in `${POSTGRES_PASSWORD}` in `docker-compose.yml`.

## Start

```sh
cd infrastructure
docker compose up -d
```

Start this before any app's `docker compose up`. It also creates the `lab_net` network that app backends join.

## Connecting

| From | Host:port | Example |
|---|---|---|
| Your machine (`.venv`, Alembic, pgAdmin) | `localhost:5433` | `postgresql+psycopg2://ehr_user:ehr_123@localhost:5433/ehr_db` |
| An app container | `postgres:5432` | `postgresql+psycopg2://ehr_user:ehr_123@postgres:5432/ehr_db` |

## Adding a database for a new app

Scripts in `initdb/` only run when the volume is empty, so after the first start a new app needs two steps:

1. Add its block to `initdb/01-create-app-databases.sql`, so fresh setups get it.
2. Create it on the running server:

   ```sh
   docker exec -it lab-postgres psql -U postgres
   ```

   Then paste the same three statements (`CREATE USER`, `CREATE DATABASE`, `REVOKE CONNECT`).

Alternatively, `docker compose down -v` followed by `docker compose up -d` recreates everything from the script, but that **deletes every app's data**.
