#!/bin/bash

# Claude Code Authentication Setup Script
# Run this from your host machine to authenticate Claude Code in the Docker container

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Claude Code Authentication Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will set up Claude Code authentication in your Orchestrate container."
echo ""

# Check if Docker container is running
if ! docker ps | grep -q orchestrate_instance; then
    echo "❌ Error: Orchestrate container is not running"
    echo ""
    echo "Please start your Orchestrate container first."
    exit 1
fi

echo "✅ Container detected"
echo ""
echo "Starting Claude Code authentication process..."
echo ""
echo "This will:"
echo "  1. Install Claude Code in the container (if not already installed)"
echo "  2. Open your browser for OAuth authentication"
echo "  3. Save the authentication token in the container"
echo ""
read -p "Press ENTER to continue..."

# Run the authentication inside the container
docker exec -it orchestrate_instance bash -c '
echo ""
echo "Checking Claude Code installation..."

if [ ! -f ~/.local/bin/claude ]; then
    echo "Installing Claude Code..."
    curl -fsSL https://claude.ai/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✅ Claude Code already installed"
fi

echo ""
echo "Starting authentication..."
echo ""
echo "Your browser will open in a moment."
echo "Complete the authentication there, then return here."
echo ""

~/.local/bin/claude setup-token

if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Authentication Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🎉 Claude Code is now authenticated and ready to use!"
    echo ""
    echo "Autonomous task execution is now enabled."
    echo ""
else
    echo ""
    echo "❌ Authentication failed"
    echo ""
    echo "Please try running this script again."
    exit 1
fi
'

echo ""
echo "Setup complete! You can close this window."
echo ""
