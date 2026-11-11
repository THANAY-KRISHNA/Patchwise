#!/bin/sh
set -e

# Run database migrations against configured DATABASE_URL
echo "Executing database migrations with Alembic..."
python -m alembic upgrade head || {
    echo "Warning: Alembic migration reported an error or database was not ready; continuing..."
}

# Hand off execution to main container process (uvicorn)
exec "$@"
