# Alembic

## Run migrations
```bash
cd services/api
source .venv/bin/activate
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/soulmatch
alembic upgrade head
```

## Create a new migration
```bash
cd services/api
source .venv/bin/activate
alembic revision -m "describe change"
```
