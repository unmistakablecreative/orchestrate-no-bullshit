#!/usr/bin/env python3
"""
Unlock Tool - Unified Version

Handles unlocking of both:
1. Pre-installed tools (already in system_settings.ndjson, just need to be marked unlocked)
2. Marketplace tools (in orchestrate_app_store.json, need to be registered)

Single action intelligently routes based on where tool is found.
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_STORE_PATH = os.path.join(BASE_DIR, "orchestrate_app_store.json")
REFERRAL_PATH = os.path.join(BASE_DIR, "container_state", "referrals.json")
IDENTITY_PATH = os.path.join(BASE_DIR, "container_state", "system_identity.json")
SYSTEM_REGISTRY = os.path.join(BASE_DIR, "system_settings.ndjson")

# JSONBin config
JSONBIN_ID = "68292fcf8561e97a50162139"
JSONBIN_KEY = "$2a$10$MoavwaWsCucy2FkU/5ycV.lBTPWoUq4uKHhCi9Y47DOHWyHFL3o2C"


def load_app_store():
    """Load app store configuration"""
    try:
        with open(APP_STORE_PATH, 'r') as f:
            data = json.load(f)
            return data.get("entries", {})
    except Exception as e:
        return {}


def load_registry():
    """Load system_settings.ndjson"""
    try:
        with open(SYSTEM_REGISTRY, 'r') as f:
            return [json.loads(line.strip()) for line in f if line.strip()]
    except Exception as e:
        return []


def save_registry(entries):
    """Save system_settings.ndjson"""
    try:
        with open(SYSTEM_REGISTRY, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        return {"status": "success"}
    except Exception as e:
        return {"error": f"Failed to save registry: {e}"}


def load_local_ledger():
    """Load user's local referral ledger"""
    try:
        with open(REFERRAL_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to load local ledger: {e}"}


def save_local_ledger(ledger):
    """Save updated local ledger"""
    try:
        with open(REFERRAL_PATH, 'w') as f:
            json.dump(ledger, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        return {"error": f"Failed to save local ledger: {e}"}


def get_user_id():
    """Get user's unique ID from system identity"""
    try:
        with open(IDENTITY_PATH, 'r') as f:
            identity = json.load(f)
            return identity.get("user_id")
    except Exception as e:
        return None


def sync_from_jsonbin():
    """Sync credits FROM JSONBin to local ledger"""
    try:
        user_id = get_user_id()
        if not user_id:
            return {"error": "No user ID found"}

        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_KEY}
        )

        if response.status_code != 200:
            return {"error": "Failed to fetch JSONBin ledger"}

        full_ledger = response.json().get("record", {})
        installs = full_ledger.get("installs", {})

        if user_id in installs:
            # Update local ledger with JSONBin data
            save_local_ledger(installs[user_id])
            return {"status": "success"}
        else:
            return {"error": f"User {user_id} not found in JSONBin"}

    except Exception as e:
        return {"error": f"JSONBin sync error: {e}"}


def sync_to_jsonbin(user_id, ledger):
    """Sync local ledger to JSONBin cloud"""
    try:
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_KEY}
        )

        if response.status_code != 200:
            return {"error": "Failed to fetch JSONBin ledger"}

        full_ledger = response.json().get("record", {})
        installs = full_ledger.get("installs", {})

        installs[user_id] = ledger

        updated = {
            "filename": "install_ledger.json",
            "installs": installs
        }

        response = requests.put(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}",
            headers={
                "Content-Type": "application/json",
                "X-Master-Key": JSONBIN_KEY
            },
            json=updated
        )

        if response.status_code == 200:
            return {"status": "success"}
        else:
            return {"error": f"JSONBin sync failed: {response.status_code}"}

    except Exception as e:
        return {"error": f"JSONBin sync error: {e}"}


def register_tool_actions(tool_name):
    """Register tool actions in system_settings.ndjson"""
    try:
        tool_script = os.path.join(BASE_DIR, "tools", f"{tool_name}.py")

        if not os.path.exists(tool_script):
            return {"error": f"Tool script not found: {tool_script}"}

        sys.path.insert(0, BASE_DIR)
        from system_settings import add_tool

        result = add_tool({"tool_name": tool_name, "script_path": tool_script})
        return result

    except Exception as e:
        return {"error": f"Failed to register actions: {e}"}


def check_claude_authentication():
    """Check if Claude Code is authenticated"""
    try:
        claude_path = os.path.expanduser("~/.local/bin/claude")

        if not os.path.exists(claude_path):
            return False

        # Run claude auth status check
        result = subprocess.run(
            [claude_path, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check if authenticated based on output or exit code
        return result.returncode == 0 or "authenticated" in result.stdout.lower()

    except Exception:
        return False


def wait_for_authentication(timeout=300, poll_interval=5):
    """
    Wait for Claude Code authentication to complete

    Args:
        timeout: Maximum time to wait in seconds (default 5 minutes)
        poll_interval: Time between checks in seconds (default 5 seconds)

    Returns:
        {"authenticated": True} if successful
        {"authenticated": False, "error": "..."} if timeout or failure
    """
    import time

    print(f"\n⏸️  Waiting for authentication to complete...", file=sys.stderr)
    print(f"   Open your browser and click 'Allow' when prompted.", file=sys.stderr)
    print(f"   Timeout: {timeout}s (checking every {poll_interval}s)\n", file=sys.stderr)

    start_time = time.time()
    attempts = 0

    while (time.time() - start_time) < timeout:
        attempts += 1

        if check_claude_authentication():
            elapsed = time.time() - start_time
            print(f"\n✅ Authentication verified! (took {elapsed:.1f}s, {attempts} checks)", file=sys.stderr)
            return {"authenticated": True}

        # Print progress dot
        print(".", end="", flush=True, file=sys.stderr)
        time.sleep(poll_interval)

    print(f"\n\n❌ Authentication timeout after {timeout}s", file=sys.stderr)
    return {
        "authenticated": False,
        "error": f"User did not complete authentication within {timeout} seconds"
    }


def run_setup_script(script_path):
    """Execute tool setup script (e.g., OAuth flow)"""
    try:
        mounted_path = os.path.join("/orchestrate_user/documents/orchestrate", script_path)
        container_path = os.path.join(BASE_DIR, script_path)

        if os.path.exists(mounted_path):
            script_full_path = mounted_path
        elif os.path.exists(container_path):
            script_full_path = container_path
        else:
            return {
                "error": f"Setup script not found",
                "tried_paths": [mounted_path, container_path]
            }

        os.chmod(script_full_path, 0o755)

        print(f"\n🔐 Running authentication setup: {script_full_path}\n", file=sys.stderr)

        result = subprocess.run(
            ["bash", script_full_path],
            timeout=300
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Authentication setup completed"
            }
        else:
            return {
                "error": "Authentication setup failed",
                "exit_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {"error": "Authentication setup timed out"}
    except Exception as e:
        return {"error": f"Setup script execution failed: {e}"}


def find_tool_location(tool_name):
    """
    Determine where tool exists:
    - 'preinstalled': exists in system_settings.ndjson
    - 'marketplace': exists in orchestrate_app_store.json
    - 'not_found': doesn't exist anywhere
    """
    # Check registry for pre-installed tool
    registry = load_registry()
    for entry in registry:
        if entry.get("tool") == tool_name and entry.get("action") == "__tool__":
            return "preinstalled", entry.get("referral_unlock_cost", 0)

    # Check app store for marketplace tool
    app_store = load_app_store()
    if tool_name in app_store:
        return "marketplace", app_store[tool_name].get("referral_unlock_cost", 0)

    return "not_found", 0


def unlock_preinstalled_tool(tool_name, cost):
    """Unlock a pre-installed tool (mark as unlocked in registry)"""
    # Sync from JSONBin first
    sync_from_jsonbin()

    # Load ledger
    ledger = load_local_ledger()
    if "error" in ledger:
        return ledger

    # Check if already unlocked
    unlocked_tools = ledger.get("tools_unlocked", [])
    if tool_name in unlocked_tools:
        return {
            "status": "already_unlocked",
            "message": f"✅ {tool_name} is already unlocked"
        }

    # Check credits
    current_credits = ledger.get("referral_credits", 0)
    if current_credits < cost:
        return {
            "error": f"Insufficient credits. Need {cost}, have {current_credits}",
            "credits_needed": cost - current_credits
        }

    # Deduct credits
    ledger["referral_credits"] -= cost
    ledger["tools_unlocked"].append(tool_name)

    # Save local ledger
    save_result = save_local_ledger(ledger)
    if "error" in save_result:
        return save_result

    # Sync to JSONBin
    user_id = get_user_id()
    if user_id:
        sync_result = sync_to_jsonbin(user_id, ledger)
        if "error" in sync_result:
            print(f"⚠️  Warning: JSONBin sync failed: {sync_result['error']}", file=sys.stderr)

    # Mark as unlocked in registry
    registry = load_registry()
    for entry in registry:
        if entry.get("tool") == tool_name and entry.get("action") == "__tool__":
            entry["locked"] = False
            entry["unlocked"] = True
            break

    save_registry(registry)

    return {
        "status": "success",
        "tool": tool_name,
        "type": "preinstalled",
        "credits_remaining": ledger["referral_credits"],
        "message": f"✅ {tool_name} unlocked! {ledger['referral_credits']} credits remaining."
    }


def unlock_marketplace_tool(tool_name, cost):
    """Unlock a marketplace tool (register + add to registry)"""
    # Sync from JSONBin first
    sync_from_jsonbin()

    app_store = load_app_store()
    tool_config = app_store.get(tool_name, {})

    # Load ledger
    ledger = load_local_ledger()
    if "error" in ledger:
        return ledger

    # Check if already unlocked
    unlocked_tools = ledger.get("tools_unlocked", [])
    if tool_name in unlocked_tools:
        return {
            "status": "already_unlocked",
            "message": f"✅ {tool_config.get('label', tool_name)} is already unlocked"
        }

    # Check credits
    current_credits = ledger.get("referral_credits", 0)
    if current_credits < cost:
        return {
            "error": f"Insufficient credits. Need {cost}, have {current_credits}",
            "credits_needed": cost - current_credits
        }

    # Deduct credits
    ledger["referral_credits"] -= cost
    ledger["tools_unlocked"].append(tool_name)

    # Save local ledger
    save_result = save_local_ledger(ledger)
    if "error" in save_result:
        return save_result

    # Sync to JSONBin
    user_id = get_user_id()
    if user_id:
        sync_result = sync_to_jsonbin(user_id, ledger)
        if "error" in sync_result:
            print(f"⚠️  Warning: JSONBin sync failed: {sync_result['error']}", file=sys.stderr)

    # Register tool actions
    register_result = register_tool_actions(tool_name)
    if "error" in register_result:
        return {
            "error": "Tool unlocked but action registration failed",
            "details": register_result["error"]
        }

    # Run setup script if specified
    if "setup_script" in tool_config:
        print(f"\n⚙️  {tool_config.get('label', tool_name)} requires authentication setup...\n", file=sys.stderr)

        setup_result = run_setup_script(tool_config["setup_script"])

        if "error" in setup_result:
            print(f"\n❌ Authentication setup script failed!\n", file=sys.stderr)
            print(f"Error: {setup_result['error']}\n", file=sys.stderr)

            if "tried_paths" in setup_result:
                print(f"Tried locations:", file=sys.stderr)
                for path in setup_result["tried_paths"]:
                    print(f"  - {path}", file=sys.stderr)

            return {
                "status": "error",
                "error": "Tool unlocked but authentication setup failed",
                "setup_error": setup_result["error"],
                "message": f"❌ {tool_config.get('label', tool_name)} unlocked but authentication failed.\n\n"
                          f"The tool is registered but cannot be used until authentication completes.\n\n"
                          f"Please run the setup script manually.",
                "unlock_message": tool_config.get("unlock_message", "")
            }

        # Wait for authentication to complete
        print(f"\n🔍 Verifying authentication status...", file=sys.stderr)
        auth_result = wait_for_authentication(timeout=300, poll_interval=5)

        if not auth_result.get('authenticated'):
            return {
                "status": "error",
                "error": "Authentication timeout",
                "message": f"❌ {tool_config.get('label', tool_name)} authentication not completed.\n\n"
                          f"{auth_result.get('error', 'User did not complete authentication.')}\n\n"
                          f"Please run the authentication setup again.",
                "unlock_message": tool_config.get("unlock_message", "")
            }

        print(f"\n✅ {tool_config.get('label', tool_name)} authenticated and ready!\n", file=sys.stderr)

    # Build success response
    response = {
        "status": "success",
        "tool": tool_name,
        "type": "marketplace",
        "label": tool_config.get("label", tool_name),
        "credits_remaining": ledger["referral_credits"],
        "unlock_message": tool_config.get("unlock_message", f"✅ {tool_config.get('label', tool_name)} unlocked!")
    }

    if "post_unlock_nudge" in tool_config:
        response["nudge"] = tool_config["post_unlock_nudge"]

    return response


def unlock_tool(tool_name):
    """
    Unified unlock function - intelligently routes to correct unlock flow

    Flow:
    1. Check if tool exists in system_settings.ndjson (pre-installed)
       → If yes: unlock_preinstalled_tool()
    2. Check if tool exists in orchestrate_app_store.json (marketplace)
       → If yes: unlock_marketplace_tool()
    3. If neither: return error
    """

    # Find where tool exists
    location, cost = find_tool_location(tool_name)

    if location == "not_found":
        return {
            "error": f"Tool '{tool_name}' not found in pre-installed tools or marketplace"
        }

    # Route to appropriate unlock function
    if location == "preinstalled":
        return unlock_preinstalled_tool(tool_name, cost)
    else:  # marketplace
        return unlock_marketplace_tool(tool_name, cost)


def list_marketplace_tools():
    """List all available marketplace tools with lock status"""
    app_store = load_app_store()
    ledger = load_local_ledger()

    if "error" in ledger:
        return ledger

    unlocked = set(ledger.get("tools_unlocked", []))
    credits = ledger.get("referral_credits", 0)

    tools = []
    for tool_name, config in app_store.items():
        tools.append({
            "name": tool_name,
            "label": config.get("label", tool_name),
            "description": config.get("description", ""),
            "cost": config.get("referral_unlock_cost", 0),
            "priority": config.get("priority", 999),
            "locked": tool_name not in unlocked,
            "requires_subscription": config.get("requires_subscription", False),
            "subscription_type": config.get("subscription_type", None),
            "requires_credentials": config.get("requires_credentials", False)
        })

    tools.sort(key=lambda x: x["priority"])

    return {
        "status": "success",
        "credits_available": credits,
        "tools": tools
    }


def get_credits_balance():
    """Get current credit balance"""
    ledger = load_local_ledger()
    if "error" in ledger:
        return ledger

    return {
        "status": "success",
        "credits": ledger.get("referral_credits", 0),
        "referral_count": ledger.get("referral_count", 0),
        "tools_unlocked": ledger.get("tools_unlocked", [])
    }


# Action registry for execution_hub
ACTIONS = {
    "unlock_tool": unlock_tool,
    "list_marketplace_tools": list_marketplace_tools,
    "get_credits_balance": get_credits_balance
}


def execute_action(action, params):
    """Execute unlock tool action"""
    if action not in ACTIONS:
        return {"error": f"Unknown action: {action}"}

    try:
        # Handle both dict params and direct tool_name string
        if isinstance(params, dict):
            tool_name = params.get("tool_name")
        else:
            tool_name = params

        if action == "unlock_tool":
            return unlock_tool(tool_name)
        else:
            return ACTIONS[action](**params if isinstance(params, dict) else {})
    except Exception as e:
        return {"error": f"Action execution failed: {e}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: unlock_tool.py <action> [tool_name]")
        print("Actions: unlock_tool, list_marketplace_tools, get_credits_balance")
        sys.exit(1)

    action = sys.argv[1]

    if action == "unlock_tool":
        if len(sys.argv) < 3:
            print("Usage: unlock_tool.py unlock_tool <tool_name>")
            sys.exit(1)
        result = unlock_tool(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif action == "list_marketplace_tools":
        result = list_marketplace_tools()
        print(json.dumps(result, indent=2))

    elif action == "get_credits_balance":
        result = get_credits_balance()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
