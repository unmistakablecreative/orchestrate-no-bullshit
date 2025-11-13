#!/usr/bin/env python3
"""
System Settings Manager - Complete Version

Handles:
- Loading/saving system_settings.ndjson
- Registering tool actions automatically from tool scripts
- Managing credentials
- Memory file tracking
- CLI route management
- Runtime refresh (pull updates while preserving user data)
"""

import os
import sys
import json
import importlib.util
import inspect
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_REGISTRY = os.path.join(BASE_DIR, "system_settings.ndjson")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
CREDENTIALS_FILE = os.path.join(TOOLS_DIR, "credentials.json")


def load_credential(key):
    """Load a credential from credentials.json"""
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            return None
        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
        return creds.get(key)
    except Exception:
        return None


def save_credential(key, value):
    """Save a credential to credentials.json"""
    try:
        creds = {}
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)

        creds[key] = value

        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)

        return {"status": "success"}
    except Exception as e:
        return {"error": f"Failed to save credential: {e}"}


def load_registry():
    """Load system_settings.ndjson as list of entries"""
    try:
        with open(SYSTEM_REGISTRY, 'r') as f:
            return [json.loads(line.strip()) for line in f if line.strip()]
    except Exception as e:
        return []


def save_registry(entries):
    """Save registry entries back to system_settings.ndjson"""
    try:
        with open(SYSTEM_REGISTRY, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        return {"status": "success"}
    except Exception as e:
        return {"error": f"Failed to save registry: {e}"}


def set_credential(params):
    """
    Set a credential for a tool.

    Required:
    - value: credential value
    - script_path: path to tool script (e.g., "tools/outline_editor.py")

    Optional:
    - key: credential key (default: inferred from script_path)

    Example:
    {"value": "sk-outline-abc123", "script_path": "tools/outline_editor.py"}
    """
    value = params.get("value")
    script_path = params.get("script_path")
    key = params.get("key")

    if not value:
        return {"status": "error", "message": "Missing required field: value"}

    if not script_path:
        return {"status": "error", "message": "Missing required field: script_path"}

    # Infer key from script_path if not provided
    if not key:
        # Extract tool name from script_path (e.g., "tools/outline_editor.py" -> "outline_api_key")
        tool_name = os.path.basename(script_path).replace(".py", "")
        key = f"{tool_name}_api_key"

    result = save_credential(key, value)

    if "error" in result:
        return result

    return {
        "status": "success",
        "message": f"Credential '{key}' set successfully",
        "key": key
    }


def add_action(params):
    """
    Add a new action to system_settings.ndjson

    Required:
    - tool: tool name
    - action: action name
    - script: script path
    - params: list of parameter names
    - example: example usage dict
    """
    tool = params.get("tool")
    action = params.get("action")
    script = params.get("script")
    action_params = params.get("params", [])
    example = params.get("example")

    if not all([tool, action, script]):
        return {"status": "error", "message": "Missing required fields: tool, action, script"}

    registry = load_registry()

    # Add action entry
    entry = {
        "tool": tool,
        "action": action,
        "script_path": script,
        "params": action_params
    }

    if example:
        entry["example"] = example

    registry.append(entry)

    save_result = save_registry(registry)
    if "error" in save_result:
        return save_result

    return {
        "status": "success",
        "message": f"Action '{action}' added to '{tool}'"
    }


def list_actions(params):
    """
    List all actions for a specific tool

    Required:
    - tool: tool name
    """
    tool = params.get("tool")

    if not tool:
        return {"status": "error", "message": "Missing required field: tool"}

    return get_tool_actions(tool)


def list_tools(params):
    """List all registered tools (alias for list_all_tools)"""
    return list_all_tools()


def add_tool(params):
    """
    Register a new tool

    Required:
    - tool: tool name
    - path: path to tool script
    """
    tool = params.get("tool")
    path = params.get("path")

    if not all([tool, path]):
        return {"status": "error", "message": "Missing required fields: tool, path"}

    return register_tool_from_script(tool, path)


def remove_tool(params):
    """
    Remove a tool from registry

    Required:
    - tool: tool name
    """
    tool = params.get("tool")

    if not tool:
        return {"status": "error", "message": "Missing required field: tool"}

    registry = load_registry()

    # Remove all entries for this tool
    original_count = len(registry)
    registry = [entry for entry in registry if entry.get("tool") != tool]
    removed_count = original_count - len(registry)

    if removed_count == 0:
        return {"status": "error", "message": f"Tool '{tool}' not found in registry"}

    save_result = save_registry(registry)
    if "error" in save_result:
        return save_result

    return {
        "status": "success",
        "message": f"Removed {removed_count} entries for tool '{tool}'"
    }


def add_memory_file(params):
    """
    Add a file to memory tracking list

    Required:
    - path: file path to track
    """
    path = params.get("path")

    if not path:
        return {"status": "error", "message": "Missing required field: path"}

    memory_config = os.path.join(BASE_DIR, "data", "memory_files.json")

    memory_files = []
    if os.path.exists(memory_config):
        with open(memory_config, 'r') as f:
            memory_files = json.load(f)

    if path not in memory_files:
        memory_files.append(path)

    with open(memory_config, 'w') as f:
        json.dump(memory_files, f, indent=2)

    return {
        "status": "success",
        "message": f"Added '{path}' to memory tracking"
    }


def remove_memory_file(params):
    """
    Remove a file from memory tracking

    Required:
    - path: file path to remove
    """
    path = params.get("path")

    if not path:
        return {"status": "error", "message": "Missing required field: path"}

    memory_config = os.path.join(BASE_DIR, "data", "memory_files.json")

    if not os.path.exists(memory_config):
        return {"status": "error", "message": "No memory files configured"}

    with open(memory_config, 'r') as f:
        memory_files = json.load(f)

    if path not in memory_files:
        return {"status": "error", "message": f"Path '{path}' not in memory tracking"}

    memory_files.remove(path)

    with open(memory_config, 'w') as f:
        json.dump(memory_files, f, indent=2)

    return {
        "status": "success",
        "message": f"Removed '{path}' from memory tracking"
    }


def list_memory_files(params):
    """List all memory tracked files"""
    memory_config = os.path.join(BASE_DIR, "data", "memory_files.json")

    if not os.path.exists(memory_config):
        return {
            "status": "success",
            "memory_files": []
        }

    with open(memory_config, 'r') as f:
        memory_files = json.load(f)

    return {
        "status": "success",
        "memory_files": memory_files
    }


def add_cli_route(params):
    """
    Add a CLI command route

    Required:
    - action_name: name of the action
    - command: command to execute
    """
    action_name = params.get("action_name")
    command = params.get("command")

    if not all([action_name, command]):
        return {"status": "error", "message": "Missing required fields: action_name, command"}

    cli_config = os.path.join(BASE_DIR, "data", "cli_routes.json")

    routes = {}
    if os.path.exists(cli_config):
        with open(cli_config, 'r') as f:
            routes = json.load(f)

    routes[action_name] = command

    with open(cli_config, 'w') as f:
        json.dump(routes, f, indent=2)

    return {
        "status": "success",
        "message": f"Added CLI route '{action_name}'"
    }


def remove_cli_route(params):
    """
    Remove a CLI command route

    Required:
    - action_name: name of the action to remove
    """
    action_name = params.get("action_name")

    if not action_name:
        return {"status": "error", "message": "Missing required field: action_name"}

    cli_config = os.path.join(BASE_DIR, "data", "cli_routes.json")

    if not os.path.exists(cli_config):
        return {"status": "error", "message": "No CLI routes configured"}

    with open(cli_config, 'r') as f:
        routes = json.load(f)

    if action_name not in routes:
        return {"status": "error", "message": f"Route '{action_name}' not found"}

    del routes[action_name]

    with open(cli_config, 'w') as f:
        json.dump(routes, f, indent=2)

    return {
        "status": "success",
        "message": f"Removed CLI route '{action_name}'"
    }


def list_cli_routes(params):
    """List all CLI routes"""
    cli_config = os.path.join(BASE_DIR, "data", "cli_routes.json")

    if not os.path.exists(cli_config):
        return {
            "status": "success",
            "routes": {}
        }

    with open(cli_config, 'r') as f:
        routes = json.load(f)

    return {
        "status": "success",
        "routes": routes
    }


def build_working_memory(params):
    """Build working memory from tracked files"""
    memory_config = os.path.join(BASE_DIR, "data", "memory_files.json")

    if not os.path.exists(memory_config):
        return {
            "status": "success",
            "message": "No memory files configured",
            "working_memory": {}
        }

    with open(memory_config, 'r') as f:
        memory_files = json.load(f)

    working_memory = {}

    for file_path in memory_files:
        full_path = os.path.join(BASE_DIR, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    working_memory[file_path] = data
            except Exception:
                pass

    # Save to working_memory.json
    output_path = os.path.join(BASE_DIR, "data", "working_memory.json")
    with open(output_path, 'w') as f:
        json.dump(working_memory, f, indent=2)

    return {
        "status": "success",
        "message": "Working memory built successfully",
        "files_loaded": len(working_memory)
    }


def list_supported_actions(params):
    """List all supported actions in the system"""
    registry = load_registry()

    actions = []
    for entry in registry:
        if entry.get("action") != "__tool__":
            actions.append({
                "tool": entry.get("tool"),
                "action": entry.get("action"),
                "params": entry.get("params", [])
            })

    return {
        "status": "success",
        "actions": actions
    }


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


def refresh_orchestrate_runtime(params):
    """Alias for refresh_runtime"""
    return refresh_runtime()


# Action registry for execution_hub
ACTIONS = {
    "set_credential": set_credential,
    "add_action": add_action,
    "list_actions": list_actions,
    "list_tools": list_tools,
    "add_tool": add_tool,
    "remove_tool": remove_tool,
    "add_memory_file": add_memory_file,
    "remove_memory_file": remove_memory_file,
    "list_memory_files": list_memory_files,
    "add_cli_route": add_cli_route,
    "remove_cli_route": remove_cli_route,
    "list_cli_routes": list_cli_routes,
    "build_working_memory": build_working_memory,
    "list_supported_actions": list_supported_actions,
    "register_tool_from_script": register_tool_from_script,
    "get_tool_actions": get_tool_actions,
    "list_all_tools": list_all_tools,
    "mark_tool_unlocked": mark_tool_unlocked,
    "refresh_runtime": refresh_runtime,
    "refresh_orchestrate_runtime": refresh_orchestrate_runtime
}


def execute_action(action, params):
    """Execute system_settings action"""
    if action not in ACTIONS:
        return {"error": f"Unknown action: {action}"}

    try:
        return ACTIONS[action](params)
    except Exception as e:
        return {"error": f"Action execution failed: {e}"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('action', help='Action to perform')
    parser.add_argument('--params', type=str, help='JSON params')
    args = parser.parse_args()

    params = json.loads(args.params) if args.params else {}

    if args.action in ACTIONS:
        result = ACTIONS[args.action](params)
    else:
        result = {"error": f"Unknown action: {args.action}"}

    print(json.dumps(result, indent=2))
