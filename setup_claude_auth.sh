#!/bin/bash
# Claude Code Authentication Setup
# Handles OAuth flow for Claude Assistant subscription authentication

echo "======================================"
echo "   Claude Code Authentication Setup"
echo "======================================"
echo ""

# Get container name
CONTAINER_NAME=${ORCHESTRATE_CONTAINER:-orchestrate_instance}

# Read ngrok URL from container
NGROK_URL=$(docker exec $CONTAINER_NAME cat /opt/orchestrate-core-runtime/data/ngrok.json 2>/dev/null | jq -r '.domain' 2>/dev/null || echo "")

if [ -z "$NGROK_URL" ]; then
    echo "❌ Error: ngrok domain not found in container at /opt/orchestrate-core-runtime/data/ngrok.json"
    exit 1
fi

echo "🔐 Setting up Claude Code authentication..."
echo "📡 Using ngrok callback: https://${NGROK_URL}/auth/callback"
echo ""

# Check if Claude Code is installed in container
CLAUDE_PATH="/home/orchestrate/.local/bin/claude"
if ! docker exec $CONTAINER_NAME test -f "$CLAUDE_PATH"; then
    echo "❌ Claude Code not installed in container!"
    echo "Installing Claude Code in container..."
    docker exec $CONTAINER_NAME bash -c "curl -sSL https://claude.ai/install.sh | bash"

    if [ $? -ne 0 ]; then
        echo "❌ Claude Code installation failed"
        exit 1
    fi
    echo "✅ Claude Code installed"
fi

echo "🌐 Starting OAuth authentication flow..."
echo "   Your browser will open in a moment."
echo "   Click 'Allow' to authorize Claude Code."
echo ""

# Run setup-token inside container with ngrok callback
docker exec -it $CONTAINER_NAME bash -c "export CLAUDE_CODE_CALLBACK_URL='https://${NGROK_URL}/auth/callback' && $CLAUDE_PATH setup-token"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Authentication successful!"
    echo ""
    echo "🎯 Claude Assistant is now ready for autonomous task execution."
    echo ""
    echo "📋 Example task:"
    echo "   curl -X POST http://localhost:8000/execute_task \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"tool_name\":\"claude_assistant\",\"action\":\"assign_task\",\"params\":{\"task_id\":\"test_001\",\"description\":\"Create a hello world Python script\"}}'"
    echo ""
    exit 0
else
    echo ""
    echo "❌ Authentication failed"
    echo "   Please try again or check your Claude subscription status."
    echo ""
    exit 1
fi