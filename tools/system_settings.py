#!/usr/bin/env python3
"""
System Settings Manager

Handles:
- Loading/saving system_settings.ndjson
- Registering tool actions automatically from tool scripts
- Merging unlock status with tool registry
- Runtime refresh (pull updates while preserving user data)
"""

import os
import sys
import json
import importlib.util
import inspect
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_REGISTRY = os.path.join(BASE_DIR, "system_settings.ndjson")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")


def load_registry():
    """Load system_settings.ndjson as list of entries"""
    try:
        with open(SYSTEM_REGISTRY, 'r') as f:
            return [json.loads(line.strip()) for line in f if line.strip()]
    except Exception as e:
        return {"error": f"Failed to load registry: {e}"}


def save_registry(entries):
    """Save registry entries back to system_settings.ndjson"""
    try:
        with open(SYSTEM_REGISTRY, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        return {"status": "success"}
    except Exception as e:
        return {"error": f"Failed to save registry: {e}"}


def extract_actions_from_script(tool_script_path):
    """
    Extract actions from tool script by looking for ACTIONS dict
    
    Returns list of action definitions with parameters
    """
    try:
        # Load the tool module
        spec = importlib.util.spec_from_file_location("tool_module", tool_script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for ACTIONS dictionary
        if not hasattr(module, 'ACTIONS'):
            return {"error": f"Tool script has no ACTIONS dictionary"}
        
        actions_dict = module.ACTIONS
        
        # Extract action metadata
        actions = []
        for action_name, action_func in actions_dict.items():
            # Get function signature
            sig = inspect.signature(action_func)
            params = []
            
            for param_name, param in sig.parameters.items():
                param_info = {
                    "name": param_name,
                    "required": param.default == inspect.Parameter.empty
                }
                
                # Try to infer type from annotation
                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = param.annotation.__name__
                
                params.append(param_info)
            
            # Get docstring if available
            description = action_func.__doc__ or f"Execute {action_name}"
            description = description.strip().split('\n')[0]  # First line only
            
            actions.append({
                "action": action_name,
                "description": description,
                "parameters": params
            })
        
        return {"status": "success", "actions": actions}
        
    except Exception as e:
        return {"error": f"Failed to extract actions: {e}"}


def register_tool_from_script(tool_name, tool_script_path=None):
    """
    Register a tool and all its actions in system_settings.ndjson
    
    Args:
        tool_name: Name of the tool (e.g., "claude_assistant")
        tool_script_path: Path to tool script (optional, will auto-detect)
    
    Returns:
        {"status": "success"} or {"error": "message"}
    """
    
    # Auto-detect script path if not provided
    if tool_script_path is None:
        tool_script_path = os.path.join(TOOLS_DIR, f"{tool_name}.py")
    
    if not os.path.exists(tool_script_path):
        return {"error": f"Tool script not found: {tool_script_path}"}
    
    # Extract actions from script
    extract_result = extract_actions_from_script(tool_script_path)
    if "error" in extract_result:
        return extract_result
    
    actions = extract_result["actions"]
    
    # Load current registry
    registry = load_registry()
    if "error" in registry:
        return registry
    
    # Remove any existing entries for this tool
    registry = [entry for entry in registry 
                if entry.get("tool") != tool_name]
    
    # Add tool header entry
    registry.append({
        "tool": tool_name,
        "action": "__tool__",
        "description": f"{tool_name} tool",
        "unlocked": True  # Newly unlocked tools are available
    })
    
    # Add action entries
    for action in actions:
        entry = {
            "tool": tool_name,
            "action": action["action"],
            "description": action["description"]
        }
        
        # Add parameters if present
        if action["parameters"]:
            entry["parameters"] = action["parameters"]
        
        registry.append(entry)
    
    # Save updated registry
    save_result = save_registry(registry)
    if "error" in save_result:
        return save_result
    
    return {
        "status": "success",
        "tool": tool_name,
        "actions_registered": len(actions)
    }


def get_tool_actions(tool_name):
    """Get all registered actions for a tool"""
    registry = load_registry()
    if "error" in registry:
        return registry
    
    actions = [entry for entry in registry 
               if entry.get("tool") == tool_name 
               and entry.get("action") != "__tool__"]
    
    return {
        "status": "success",
        "tool": tool_name,
        "actions": actions
    }


def list_all_tools():
    """List all registered tools with their unlock status"""
    registry = load_registry()
    if "error" in registry:
        return registry
    
    # Get tool headers
    tools = {}
    for entry in registry:
        if entry.get("action") == "__tool__":
            tool_name = entry.get("tool")
            tools[tool_name] = {
                "name": tool_name,
                "unlocked": entry.get("unlocked", False),
                "description": entry.get("description", "")
            }
    
    return {
        "status": "success",
        "tools": list(tools.values())
    }


def mark_tool_unlocked(tool_name):
    """Mark a tool as unlocked in the registry"""
    registry = load_registry()
    if "error" in registry:
        return registry
    
    # Find tool header and mark as unlocked
    updated = False
    for entry in registry:
        if entry.get("tool") == tool_name and entry.get("action") == "__tool__":
            entry["unlocked"] = True
            updated = True
            break
    
    if not updated:
        return {"error": f"Tool {tool_name} not found in registry"}
    
    save_result = save_registry(registry)
    if "error" in save_result:
        return save_result
    
    return {"status": "success", "tool": tool_name}


def refresh_runtime():
    """
    Pull latest updates from repo while preserving user data
    
    Protected items:
    - data/ directory (credentials, queues, all user data)
    - container_state/ (system identity, referrals)
    - User's unlock status in registry
    
    Updated items:
    - orchestrate_app_store.json (new tools appear)
    - Tool scripts (bug fixes, improvements)
    - System messages (update_messages.json)
    - New actions for existing tools
    """
    try:
        # Save current user state before pulling
        referral_path = os.path.join(BASE_DIR, "container_state", "referrals.json")
        unlocked_tools = set()
        user_credits = 0
        
        if os.path.exists(referral_path):
            with open(referral_path, 'r') as f:
                referral_data = json.load(f)
                unlocked_tools = set(referral_data.get("tools_unlocked", []))
                user_credits = referral_data.get("referral_credits", 0)
        
        # Pull latest changes from repo
        result = subprocess.run(
            ["git", "-C", BASE_DIR, "pull"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "error": "Git pull failed",
                "details": result.stderr
            }
        
        # Restore user's unlock status in registry
        registry = load_registry()
        if "error" not in registry:
            for entry in registry:
                tool_name = entry.get("tool")
                if entry.get("action") == "__tool__" and tool_name in unlocked_tools:
                    entry["unlocked"] = True
            
            save_registry(registry)
        
        # Force refresh of update_messages.json from repo
        repo_messages = os.path.join(BASE_DIR, "data", "update_messages.json")
        git_messages = os.path.join(BASE_DIR, ".git", "..", "data", "update_messages.json")
        
        if os.path.exists(git_messages):
            shutil.copy(git_messages, repo_messages)
        
        return {
            "status": "success",
            "message": "Runtime refreshed successfully",
            "git_output": result.stdout.strip(),
            "tools_preserved": list(unlocked_tools),
            "credits_preserved": user_credits
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "Git pull timed out"}
    except Exception as e:
        return {"error": f"Runtime refresh failed: {e}"}


# Action registry for execution_hub
ACTIONS = {
    "register_tool_from_script": register_tool_from_script,
    "get_tool_actions": get_tool_actions,
    "list_all_tools": list_all_tools,
    "mark_tool_unlocked": mark_tool_unlocked,
    "refresh_runtime": refresh_runtime
}


def execute_action(action, params):
    """Execute system_settings action"""
    if action not in ACTIONS:
        return {"error": f"Unknown action: {action}"}
    
    try:
        return ACTIONS[action](**params)
    except Exception as e:
        return {"error": f"Action execution failed: {e}"}


if __name__ == "__main__":
    # CLI usage
    if len(sys.argv) < 2:
        print("Usage: system_settings.py <action> [params...]")
        print("Actions: register_tool_from_script, get_tool_actions, list_all_tools, refresh_runtime")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "register_tool_from_script":
        if len(sys.argv) < 3:
            print("Usage: system_settings.py register_tool_from_script <tool_name>")
            sys.exit(1)
        result = register_tool_from_script(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif action == "get_tool_actions":
        if len(sys.argv) < 3:
            print("Usage: system_settings.py get_tool_actions <tool_name>")
            sys.exit(1)
        result = get_tool_actions(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif action == "list_all_tools":
        result = list_all_tools()
        print(json.dumps(result, indent=2))
    
    elif action == "refresh_runtime":
        result = refresh_runtime()
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)