#!/bin/bash
export PYTHONPATH="$PYTHONPATH:/opt/orchestrate-core-runtime"
USER_DIR="/orchestrate_user"
STATE_DIR="/container_state"
OUTPUT_DIR="/app"
RUNTIME_DIR="/tmp/runtime"
mkdir -p "$USER_DIR/dropzone"
mkdir -p "$USER_DIR/vault/watch_books"
mkdir -p "$USER_DIR/vault/watch_transcripts"
mkdir -p "$USER_DIR/orchestrate_exports/markdown"
mkdir -p "$STATE_DIR"

# Prompt if not passed in
if [ -z "$NGROK_TOKEN" ]; then
  read -p "🔐 Enter your ngrok authtoken: " NGROK_TOKEN
fi
if [ -z "$NGROK_DOMAIN" ]; then
  read -p "🌐 Enter your ngrok domain (e.g. clever-bear.ngrok-free.app): " NGROK_DOMAIN
fi

export NGROK_TOKEN
export NGROK_DOMAIN
export DOMAIN="$NGROK_DOMAIN"
export SAFE_DOMAIN=$(echo "$NGROK_DOMAIN" | sed 's|https://||g' | sed 's|[-.]|_|g')

IDENTITY_FILE="$STATE_DIR/system_identity.json"
if [ ! -f "$IDENTITY_FILE" ]; then
  UUID=$(cat /proc/sys/kernel/random/uuid)
  USER_ID="orch-${UUID}"
  TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "{\"user_id\": \"$USER_ID\", \"installed_at\": \"$TIMESTAMP\"}" > "$IDENTITY_FILE"
  
  # Ledger sync
  BIN_ID="68292fcf8561e97a50162139"
  API_KEY='$2a$10$MoavwaWsCucy2FkU/5ycV.lBTPWoUq4uKHhCi9Y47DOHWyHFL3o2C'
  
  # DEBUG: Check what's in both directories
  echo "DEBUG: Contents of /app:"
  ls -la /app/
  echo "DEBUG: Contents of /referral_data:"
  ls -la /referral_data/
  echo "DEBUG: Looking for: /referral_data/referrer.txt"
  
  if [ -f "/referral_data/referrer.txt" ]; then
    REFERRER_ID=$(cat "/referral_data/referrer.txt" | tr -d '\n\r' | xargs)
    echo "DEBUG: Found referrer ID: '$REFERRER_ID'"
    echo "DEBUG: Referrer ID length: ${#REFERRER_ID}"
  else
    REFERRER_ID=""
    echo "DEBUG: No referrer file found"
  fi
  
  echo "DEBUG: Fetching ledger from JSONBin..."
  LEDGER=$(curl -s -X GET "https://api.jsonbin.io/v3/b/$BIN_ID/latest" -H "X-Master-Key: $API_KEY")
  INSTALLS=$(echo "$LEDGER" | jq '.record.installs')
  
  # Add new user entry
  INSTALLS=$(echo "$INSTALLS" | jq --arg uid "$USER_ID" --arg ts "$TIMESTAMP" \
    '.[$uid] = { referral_count: 0, referral_credits: 3, tools_unlocked: ["json_manager"], timestamp: $ts }')
  
  if [ "$REFERRER_ID" != "" ]; then
    echo "DEBUG: About to credit referrer: '$REFERRER_ID'"
    # Check if referrer exists
    REFERRER_EXISTS=$(echo "$INSTALLS" | jq --arg rid "$REFERRER_ID" 'has($rid)')
    echo "DEBUG: Referrer exists in ledger: $REFERRER_EXISTS"
    
    if [ "$REFERRER_EXISTS" = "true" ]; then
      CURRENT_CREDITS=$(echo "$INSTALLS" | jq --arg rid "$REFERRER_ID" '.[$rid].referral_credits')
      echo "DEBUG: Current referrer credits: $CURRENT_CREDITS"
      
      INSTALLS=$(echo "$INSTALLS" | jq --arg rid "$REFERRER_ID" \
        'if .[$rid] != null then .[$rid].referral_count += 1 | .[$rid].referral_credits += 3 else . end')
      
      NEW_CREDITS=$(echo "$INSTALLS" | jq --arg rid "$REFERRER_ID" '.[$rid].referral_credits')
      echo "DEBUG: New referrer credits: $NEW_CREDITS"
      echo "DEBUG: Referrer crediting completed successfully"
    else
      echo "DEBUG: ERROR - Referrer ID not found in ledger!"
    fi
  else
    echo "DEBUG: No referrer to credit (empty or missing referrer.txt)"
  fi
  
  echo "DEBUG: Updating JSONBin ledger..."
  FINAL=$(jq -n --argjson installs "$INSTALLS" '{filename: "install_ledger.json", installs: $installs}')
  echo "$FINAL" | curl -s -X PUT "https://api.jsonbin.io/v3/b/$BIN_ID" \
    -H "Content-Type: application/json" -H "X-Master-Key: $API_KEY" --data @-
  echo "DEBUG: JSONBin update completed"
  
  echo '{ "referral_count": 0, "referral_credits": 3, "tools_unlocked": ["json_manager"] }' > "$STATE_DIR/referrals.json"
fi

RUNTIME_DIR="/opt/orchestrate-core-runtime"
if [ ! -d "$RUNTIME_DIR/.git" ]; then
  git clone https://github.com/unmistakablecreative/orchestrate-no-bullshit.git "$RUNTIME_DIR"
else
  cd "$RUNTIME_DIR" && git pull
fi

mkdir -p "$RUNTIME_DIR/data"
echo '{ "token": "'$NGROK_TOKEN'", "domain": "'$NGROK_DOMAIN'" }' > "$RUNTIME_DIR/data/ngrok.json"
cd "$RUNTIME_DIR"

# Writable GPT output path inside Docker (host-mapped)
GPT_FILE="/orchestrate_user/_paste_into_gpt.txt"
rm -f "$GPT_FILE"

if [ -f "openapi_template.yaml" ] && [ -f "instructions_template.json" ]; then
  envsubst < openapi_template.yaml > /orchestrate_user/openapi.yaml
  envsubst < instructions_template.json > /orchestrate_user/custom_instructions.json
  echo "📎 === CUSTOM INSTRUCTIONS ===" > "$GPT_FILE"
  cat /orchestrate_user/custom_instructions.json >> "$GPT_FILE"
  echo -e "\n\n📎 === OPENAPI.YAML ===" >> "$GPT_FILE"
  cat /orchestrate_user/openapi.yaml >> "$GPT_FILE"
else
  echo "⚠️ Template files missing. You can still run Orchestrate." > "$GPT_FILE"
fi

# Write Claude auth setup script directly to mounted volume
cat > /orchestrate_user/setup_claude_auth.sh << 'EOFAUTH'
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
EOFAUTH

chmod +x /orchestrate_user/setup_claude_auth.sh

echo ""
echo "📄 Instruction file content:"
cat "$GPT_FILE"

# Launch tunnel + FastAPI
ngrok config add-authtoken "$NGROK_TOKEN"
ngrok http --domain="$NGROK_DOMAIN" 8000 > /dev/null &
sleep 3
exec uvicorn jarvis:app --host 0.0.0.0 --port 8000