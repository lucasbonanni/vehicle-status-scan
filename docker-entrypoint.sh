#!/bin/bash
# Entrypoint script for FastAPI backend container
# Runs database migrations and seeds test data before starting the server

set -e

echo "🚀 Starting Vehicle Inspection API Backend"
echo "==========================================="

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if pg_isready -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -d "${DB_NAME:-vehicle_inspection}" 2>/dev/null; then
        echo "✓ Database is ready"
        break
    fi
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "✗ Database failed to start in time"
    exit 1
fi

# Run database migrations
echo ""
echo "🔄 Running database migrations..."
cd /app
if ! alembic upgrade head; then
    echo "✗ Migration failed"
    exit 1
fi
echo "✓ Migrations completed"

# Seed test data (only if this is a development environment)
if [ "${SEED_TEST_DATA:-false}" = "true" ]; then
    echo ""
    echo "📋 Seeding test data..."
    if ! python3 scripts/seed_test_data.py; then
        echo "⚠ Test data seeding failed (continuing...)"
    else
        echo "✓ Test data seeded successfully"
    fi
fi

# Start the API server
echo ""
echo "🎯 Starting FastAPI server..."
echo "==========================================="
exec uvicorn src.vehicle_inspection.presentation.api.main:app --host 0.0.0.0 --port 8000 --reload
