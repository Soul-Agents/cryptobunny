#!/bin/bash

# Set environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Ensure the required environment variables are set
if [ -z "$DEFAULT_CLIENT_ID" ] || [ -z "$AGENT_NAME" ]; then
    echo "Warning: DEFAULT_CLIENT_ID and/or AGENT_NAME not set in .env"
    echo "The application will attempt to load configuration from the database"
fi

# Check if PORT environment variable is set, otherwise use default
PORT=${PORT:-5000}
echo "Starting API server on port $PORT"

# Start the server with Gunicorn for production
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Running in development mode"
    python api.py
else
    echo "Running in production mode with Gunicorn"
    gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 api:app
fi 