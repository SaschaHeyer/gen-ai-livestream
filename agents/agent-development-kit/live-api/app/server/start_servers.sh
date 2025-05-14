#!/bin/bash

# Start the ADK multimodal server
echo "Starting ADK multimodal server on port 8765..."
python multimodal_server_adk.py &
ADK_PID=$!

# Wait a moment to ensure the server starts properly
sleep 2

echo "ADK multimodal server running with PID: $ADK_PID"
echo ""
echo "Press Ctrl+C to stop the server"

# Trap Ctrl+C to properly shut down server
trap "echo 'Stopping server...'; kill $ADK_PID; exit 0" INT

# Wait until the user presses Ctrl+C
wait