#!/bin/bash

set -e

# Configure ngrok with auth token
if [ -n "$NGROK_AUTH_TOKEN" ]; then
    echo "🔑 Configuring ngrok with auth token..."
    ngrok config add-authtoken "$NGROK_AUTH_TOKEN"
else
    echo "⚠️  NGROK_AUTH_TOKEN not set. Webapp will run without ngrok tunnel."
fi

# Start FastAPI app in background
echo "🚀 Starting FastAPI app..."
uvicorn app.services.webapp.app:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
UVICORN_PID=$!

# Give the app time to start
sleep 5

# Verify FastAPI is running
if ! kill -0 $UVICORN_PID 2>/dev/null; then
    echo "❌ FastAPI failed to start"
    cat /tmp/uvicorn.log
    exit 1
fi

echo "✅ FastAPI started (PID: $UVICORN_PID)"

# Start ngrok tunnel and save public URL
if [ -n "$NGROK_AUTH_TOKEN" ]; then
    echo "🌐 Starting ngrok tunnel..."
    ngrok http http://localhost:8000 --log=stdout > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!
    sleep 8
    
    # Extract ngrok URL with retry logic
    for i in {1..15}; do
        echo "📡 Attempting to retrieve ngrok URL (attempt $i/15)..."
        
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*' | head -1 | cut -d'"' -f4 || echo "")
        
        if [ -n "$NGROK_URL" ]; then
            echo "=========================================="
            echo "✅ Webapp is live at: $NGROK_URL"
            echo "=========================================="
            
            # Save URL to file AND environment for bot container to read
            echo "$NGROK_URL" > /tmp/ngrok_url.txt
            export NGROK_PUBLIC_URL="$NGROK_URL"
            
            # Create a marker file that other containers can check
            mkdir -p /tmp/shared
            echo "$NGROK_URL" > /tmp/shared/ngrok_url.txt
            
            break
        fi
        
        sleep 1
    done
    
    if [ -z "$NGROK_URL" ]; then
        echo "❌ Could not retrieve ngrok URL after retries"
        echo "ngrok logs:"
        cat /tmp/ngrok.log
    fi
    
    # Keep container running
    wait $UVICORN_PID
else
    echo "⚠️  NGROK_AUTH_TOKEN not set. Running FastAPI only (no ngrok)."
    wait $UVICORN_PID
fi