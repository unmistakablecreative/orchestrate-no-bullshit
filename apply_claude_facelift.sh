#!/bin/bash
# Apply Orchestrate Claude Code configuration
# Called by unlock_tool.py when unlocking claude_assistant

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/claude_config_template"
CLAUDE_DIR="/home/orchestrate/.claude"

echo "🎨 Applying Orchestrate Claude Code configuration..."

# Create .claude directory if it doesn't exist
mkdir -p "$CLAUDE_DIR"
mkdir -p "$CLAUDE_DIR/hooks"

# Copy CLAUDE.md
if [ -f "$TEMPLATE_DIR/CLAUDE.md" ]; then
    cp "$TEMPLATE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
    echo "✓ Installed CLAUDE.md"
fi

# Copy settings.json
if [ -f "$TEMPLATE_DIR/settings.json" ]; then
    cp "$TEMPLATE_DIR/settings.json" "$CLAUDE_DIR/settings.json"
    echo "✓ Installed settings.json (hooks + permissions)"
fi

# Copy hook scripts
if [ -f "$TEMPLATE_DIR/hooks/inject_schemas.py" ]; then
    cp "$TEMPLATE_DIR/hooks/inject_schemas.py" "$CLAUDE_DIR/hooks/inject_schemas.py"
    chmod +x "$CLAUDE_DIR/hooks/inject_schemas.py"
    echo "✓ Installed inject_schemas.py hook"
fi

echo ""
echo "🎉 Claude Code configured for Orchestrate!"
echo ""
echo "Features enabled:"
echo "  • Auto-schema injection (saves tokens)"
echo "  • Data file protection (prevents breaking things)"
echo "  • execution_hub.py enforcement (clean API usage)"
echo ""

exit 0
