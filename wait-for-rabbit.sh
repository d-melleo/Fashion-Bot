#!/bin/sh
set -e

HOST="${RABBITMQ_HOST:-rabbitmq}"
PORT="${RABBITMQ_PORT:-5672}"

echo "⏳ Waiting for RabbitMQ at ${HOST}:${PORT}..."

# Wait for RabbitMQ to accept connections
until nc -z "$HOST" "$PORT"; do
    sleep 2
done

echo "✅ RabbitMQ is up at ${HOST}:${PORT}"

# Execute the rest of the command
echo "🚀 Starting: $@"
exec "$@"