#!/bin/bash
# Setup Claude Code Authentication
# Auto-triggered during first-run or auth failures

set -e

echo "🔐 Setting up Claude Code authentication..."

# Check if Claude Code is installed
if ! command -v claude &> /dev/null; then
    echo "❌ Claude Code CLI not found in PATH"
    echo "Expected location: ~/.local/bin/claude"
    exit 1
fi

# Check current auth status
if claude auth status 2>&1 | grep -q "authenticated"; then
    echo "✅ Claude Code already authenticated"
    exit 0
fi

echo ""
echo "📋 To authenticate Claude Code:"
echo "   1. Visit https://claude.ai/settings/developer"
echo "   2. Generate a new API key"
echo "   3. Paste it below"
echo ""

# Run Claude auth login (interactive)
claude auth login

# Verify authentication worked
if claude auth status 2>&1 | grep -q "authenticated"; then
    echo "✅ Claude Code authentication successful"
    exit 0
else
    echo "❌ Claude Code authentication failed"
    exit 1
fi
