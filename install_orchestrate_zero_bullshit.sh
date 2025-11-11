#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     ORCHESTRATE - ZERO BULLSHIT INSTALLER                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# === Hardcoded credentials for testing ===
NGROK_TOKEN="2up3BdDUd9Var3zdSB0ym2gJv0C_5PRgyUMNUTMR2ksN6VXXV"
NGROK_DOMAIN="supposedly-faithful-termite.ngrok-free.app"

# === Step 1: Check Docker ===
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker Desktop first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker daemon not running! Please start Docker Desktop."
    exit 1
fi

echo "✅ Docker ready"
echo ""

# === Step 2: Setup directories ===
echo "📁 Setting up directories..."
ORCHESTRATE_DIR="$HOME/Documents/Orchestrate"
mkdir -p "$ORCHESTRATE_DIR"
echo "✅ Created $ORCHESTRATE_DIR"
echo ""

# === Step 3: Use local repo ===
echo "📦 Using local orchestrate-no-bullshit repo..."
REPO_DIR="/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit"

if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Local repo not found at $REPO_DIR"
    exit 1
fi

cd "$REPO_DIR"
echo "✅ Repo ready at $REPO_DIR"
echo ""

# === Step 5: Build Docker image ===
echo "🏗️  Building Docker image..."
docker build -t orchestrate-no-bullshit .

echo "✅ Image built"
echo ""

# === Step 6: Stop existing container (if any) ===
echo "🧹 Cleaning up old container..."
docker rm -f orchestrate_nobullshit 2>/dev/null || true
echo "✅ Cleanup done"
echo ""

# === Step 7: Start container ===
echo "🚀 Starting Orchestrate container..."
docker run -d \
  --name orchestrate_nobullshit \
  -p 8000:8000 \
  -e NGROK_TOKEN="$NGROK_TOKEN" \
  -e NGROK_DOMAIN="$NGROK_DOMAIN" \
  -v "$ORCHESTRATE_DIR:/orchestrate_user" \
  -v "$HOME/.orchestrate_state:/container_state" \
  orchestrate-no-bullshit

echo "✅ Container started"
echo ""

# === Step 8: Wait for startup ===
echo "⏳ Waiting for services to start (15s)..."
sleep 15
echo ""

# === Step 9: Test connection ===
echo "🧪 Testing connection..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "https://$NGROK_DOMAIN/execute_task" \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"check_credits","action":"check_credits","params":{}}' || echo "000")

if [ "$RESPONSE" = "200" ]; then
    echo "✅ API responding!"
else
    echo "⚠️  API might still be starting up (got HTTP $RESPONSE)"
fi
echo ""

# === Step 10: Show container logs ===
echo "📋 Container logs (last 20 lines):"
docker logs orchestrate_nobullshit --tail 20
echo ""

# === Done ===
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 INSTALLATION COMPLETE                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Your Orchestrate API: https://$NGROK_DOMAIN"
echo "📁 User directory: $ORCHESTRATE_DIR"
echo "🐳 Container name: orchestrate_nobullshit"
echo ""
echo "Next steps:"
echo "  1. Unlock claude_assistant to install Claude Code"
echo "  2. Authenticate via browser link"
echo "  3. Assign tasks autonomously"
echo ""
echo "Useful commands:"
echo "  • View logs:    docker logs -f orchestrate_nobullshit"
echo "  • Restart:      docker restart orchestrate_nobullshit"
echo "  • Stop:         docker stop orchestrate_nobullshit"
echo "  • Shell access: docker exec -it orchestrate_nobullshit bash"
echo ""
