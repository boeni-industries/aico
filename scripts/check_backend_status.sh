#!/bin/bash
# Check if backend is running and show recent scheduler activity

echo "🔍 Checking backend status..."
echo "================================"

# Check if backend is running
if ps aux | grep -q "[p]ython backend/main.py"; then
    echo "✅ Backend is running"
    PID=$(ps aux | grep "[p]ython backend/main.py" | awk '{print $2}')
    echo "   PID: $PID"
    echo "   Started: $(ps -p $PID -o lstart=)"
else
    echo "❌ Backend is NOT running"
    exit 1
fi

echo ""
echo "🔄 Checking for trigger files..."
TRIGGER_DIR="$HOME/Library/Application Support/aico/runtime/scheduler/triggers"
if [ -d "$TRIGGER_DIR" ]; then
    COUNT=$(ls -1 "$TRIGGER_DIR" 2>/dev/null | wc -l)
    echo "   Trigger files: $COUNT"
    if [ $COUNT -gt 0 ]; then
        ls -lh "$TRIGGER_DIR"
    fi
else
    echo "   Trigger directory doesn't exist"
fi

echo ""
echo "💡 The backend needs to be restarted to clear in-memory running_tasks state"
echo "   Press Ctrl+C in the backend terminal and restart it"
