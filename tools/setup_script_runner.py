#!/usr/bin/env python3
"""
Setup Script Runner - Isolated helper for running tool setup scripts

Handles execution of setup scripts for marketplace tools that require
authentication or configuration (e.g., Claude Assistant OAuth flow).

Keeps unlock_tool.py clean by isolating all setup script logic here.
"""

import os
import sys
import subprocess


def run_setup_script(script_path):
    """
    Execute a setup script from the mounted documents directory.

    Args:
        script_path: Relative path to script (e.g., "setup_claude_auth.sh")

    Returns:
        dict with status, message, and optional stdout/stderr
    """
    try:
        # Build full path to mounted setup script
        full_script_path = os.path.join("/orchestrate_user/documents/orchestrate", script_path)

        if not os.path.exists(full_script_path):
            return {
                "status": "error",
                "message": f"❌ Setup script not found at {full_script_path}"
            }

        # Make executable
        os.chmod(full_script_path, 0o755)

        print(f"🔧 Executing setup script: {full_script_path}", file=sys.stderr)

        # Execute the script
        result = subprocess.run(
            ["bash", full_script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout for OAuth flows
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "message": "✅ Authentication complete! Tool is ready to use.",
                "stdout": result.stdout
            }
        else:
            return {
                "status": "error",
                "message": f"❌ Authentication failed: {result.stderr}",
                "stdout": result.stdout,
                "returncode": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "⏱️ Authentication timed out after 5 minutes. Please try again."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Failed to run setup: {str(e)}"
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 setup_script_runner.py <script_path>")
        sys.exit(1)

    import json
    result = run_setup_script(sys.argv[1])
    print(json.dumps(result, indent=2))
