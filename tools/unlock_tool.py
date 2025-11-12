#!/usr/bin/env python3
"""
Unlock Tool - Data-Driven Version

Handles unlocking of App Store tools through referral credits.
All tool-specific behavior (costs, messages, setup) defined in orchestrate_app_store.json.

Zero hardcoded tool logic - pure config-driven execution.
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
        return {"error": f"Failed to load app store: {e}"}


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


def sync_to_jsonbin(user_id, ledger):
    """Sync local ledger to JSONBin cloud"""
    try:
        # Fetch current JSONBin state
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_KEY}
        )
        
        if response.status_code != 200:
            return {"error": "Failed to fetch JSONBin ledger"}
        
        full_ledger = response.json().get("record", {})
        installs = full_ledger.get("installs", {})
        
        # Update user's entry
        installs[user_id] = ledger
        
        # Write back to JSONBin
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
        
        # Import system_settings registration function
        sys.path.insert(0, BASE_DIR)
        from system_settings import register_tool_from_script
        
        result = register_tool_from_script(tool_name, tool_script)
        return result
        
    except Exception as e:
        return {"error": f"Failed to register actions: {e}"}


def run_setup_script(script_path):
    """Execute tool setup script (e.g., OAuth flow)"""
    try:
        full_path = os.path.join(BASE_DIR, script_path)
        
        if not os.path.exists(full_path):
            return {"error": f"Setup script not found: {full_path}"}
        
        # Make executable
        os.chmod(full_path, 0o755)
        
        # Run script
        result = subprocess.run(
            ["bash", full_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for auth flows
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "output": result.stdout
            }
        else:
            return {
                "error": "Setup script failed",
                "stderr": result.stderr
            }
            
    except Exception as e:
        return {"error": f"Setup script execution failed: {e}"}


def unlock_marketplace_tool(tool_name):
    """
    Main unlock function - data-driven from app store config
    
    Flow:
    1. Load tool config from app store
    2. Check user has enough credits
    3. Deduct credits
    4. Add to tools_unlocked
    5. Sync to JSONBin
    6. Register tool actions
    7. Run setup script if needed
    8. Return unlock message
    """
    
    # Load app store config
    app_store = load_app_store()
    if "error" in app_store:
        return app_store
    
    if tool_name not in app_store:
        return {"error": f"Tool '{tool_name}' not found in app store"}
    
    tool_config = app_store[tool_name]
    
    # Load local ledger
    ledger = load_local_ledger()
    if "error" in ledger:
        return ledger
    
    # Check if already unlocked
    unlocked_tools = ledger.get("tools_unlocked", [])
    if tool_name in unlocked_tools:
        return {
            "status": "already_unlocked",
            "message": f"✅ {tool_config['label']} is already unlocked"
        }
    
    # Check credits
    cost = tool_config.get("referral_unlock_cost", 0)
    current_credits = ledger.get("referral_credits", 0)
    
    if current_credits < cost:
        return {
            "error": f"Insufficient credits. Need {cost}, have {current_credits}",
            "credits_needed": cost - current_credits
        }
    
    # Deduct credits
    ledger["referral_credits"] -= cost
    
    # Add to unlocked tools
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
            # Non-fatal - local unlock still worked
            print(f"Warning: JSONBin sync failed: {sync_result['error']}", file=sys.stderr)
    
    # Register tool actions
    register_result = register_tool_actions(tool_name)
    if "error" in register_result:
        return {
            "error": "Tool unlocked but action registration failed",
            "details": register_result["error"]
        }
    
    # Run setup script if specified
    setup_output = None
    if "setup_script" in tool_config:
        setup_result = run_setup_script(tool_config["setup_script"])
        if "error" in setup_result:
            return {
                "status": "partial_success",
                "message": "Tool unlocked and registered, but setup script failed",
                "setup_error": setup_result["error"],
                "unlock_message": tool_config.get("unlock_message", "Tool unlocked")
            }
        setup_output = setup_result.get("output")
    
    # Build success response
    response = {
        "status": "success",
        "tool": tool_name,
        "label": tool_config["label"],
        "credits_remaining": ledger["referral_credits"],
        "unlock_message": tool_config.get("unlock_message", f"✅ {tool_config['label']} unlocked!")
    }
    
    # Add setup output if present
    if setup_output:
        response["setup_output"] = setup_output
    
    # Add post-unlock nudge if present
    if "post_unlock_nudge" in tool_config:
        response["nudge"] = tool_config["post_unlock_nudge"]
    
    return response


def list_marketplace_tools():
    """List all available marketplace tools with lock status"""
    app_store = load_app_store()
    if "error" in app_store:
        return app_store
    
    ledger = load_local_ledger()
    if "error" in ledger:
        return ledger
    
    unlocked = set(ledger.get("tools_unlocked", []))
    credits = ledger.get("referral_credits", 0)
    
    tools = []
    for tool_name, config in app_store.items():
        tools.append({
            "name": tool_name,
            "label": config["label"],
            "description": config["description"],
            "cost": config.get("referral_unlock_cost", 0),
            "priority": config.get("priority", 999),
            "locked": tool_name not in unlocked,
            "requires_subscription": config.get("requires_subscription", False),
            "subscription_type": config.get("subscription_type", None)
        })
    
    # Sort by priority
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
    "unlock_marketplace_tool": unlock_marketplace_tool,
    "list_marketplace_tools": list_marketplace_tools,
    "get_credits_balance": get_credits_balance
}


def execute_action(action, params):
    """Execute unlock tool action"""
    if action not in ACTIONS:
        return {"error": f"Unknown action: {action}"}
    
    try:
        return ACTIONS[action](**params)
    except Exception as e:
        return {"error": f"Action execution failed: {e}"}


if __name__ == "__main__":
    # CLI usage
    if len(sys.argv) < 2:
        print("Usage: unlock_tool.py <action> [params...]")
        print("Actions: unlock_marketplace_tool, list_marketplace_tools, get_credits_balance")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "unlock_marketplace_tool":
        if len(sys.argv) < 3:
            print("Usage: unlock_tool.py unlock_marketplace_tool <tool_name>")
            sys.exit(1)
        result = unlock_marketplace_tool(sys.argv[2])
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