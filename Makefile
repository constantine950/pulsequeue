# PulseQueue — dev commands

.PHONY: dev db-up db-down db-reset schema

# Start the API server with hot reload
dev:
	uvicorn backend.main:app --reload --port 8000

# Start Redis via Docker
db-up:
	docker run -d --name pulsequeue-redis -p 6379:6379 redis:7 || docker start pulsequeue-redis

# Stop Redis
db-down:
	docker stop pulsequeue-redis

# Drop and recreate the pulsequeue database, rerun schema
db-reset:
	psql -U postgres -c "DROP DATABASE IF EXISTS pulsequeue;"
	psql -U postgres -c "CREATE DATABASE pulsequeue;"
	psql -U postgres -d pulsequeue -f backend/db/schema.sql
	@echo "Database reset complete"

# Apply schema to existing database
schema:
	psql -U postgres -d pulsequeue -f backend/db/schema.sql

