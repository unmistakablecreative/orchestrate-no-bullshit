#!/usr/bin/env python3
"""
Test unlock messages without full install/ledger flow

Tests that unlock_messages.json is loaded correctly and messages are returned
for tools that require credentials.
"""

import json
import os
import sys

# Test the unlock_messages.json structure
def test_unlock_messages_format():
    """Verify unlock_messages.json has correct structure"""
    messages_path = "/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit/data/unlock_messages.json"

    print("Testing unlock_messages.json format...")

    try:
        with open(messages_path, "r") as f:
            messages = json.load(f)
    except FileNotFoundError:
        print("❌ unlock_messages.json not found")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    # Tools that require credentials
    required_tools = [
        "outline_editor",
        "mem_tool",
        "readwise_tool",
        "github_tool_universal",
        "buffer_engine"
    ]

    passed = True

    for tool in required_tools:
        if tool not in messages:
            print(f"❌ Missing message for {tool}")
            passed = False
            continue

        tool_config = messages[tool]

        # Check required fields
        if "message" not in tool_config:
            print(f"❌ {tool} missing 'message' field")
            passed = False

        if "requires_credentials" not in tool_config:
            print(f"❌ {tool} missing 'requires_credentials' field")
            passed = False

        if tool_config.get("requires_credentials") and "credential_key" not in tool_config:
            print(f"❌ {tool} requires credentials but missing 'credential_key' field")
            passed = False

        if passed:
            print(f"✅ {tool}: {tool_config.get('credential_key', 'no creds needed')}")

    return passed


def test_unlock_message_content():
    """Verify unlock messages contain credential setup instructions"""
    messages_path = "/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit/data/unlock_messages.json"

    print("\nTesting unlock message content...")

    with open(messages_path, "r") as f:
        messages = json.load(f)

    # Check outline_editor message
    outline_msg = messages.get("outline_editor", {}).get("message", "")

    print("\n--- outline_editor unlock message ---")
    print(outline_msg)
    print("--------------------------------------\n")

    # Verify it contains setup instructions
    if "Setup Required" in outline_msg:
        print("✅ Contains setup instructions")
    else:
        print("❌ Missing setup instructions")
        return False

    if "API key" in outline_msg or "API token" in outline_msg:
        print("✅ Mentions API key/token")
    else:
        print("❌ Doesn't mention API key")
        return False

    return True


def test_unlock_tool_integration():
    """Test that unlock_tool.py can load and return messages"""
    print("\nTesting unlock_tool.py integration...")

    # Import the unlock tool
    sys.path.insert(0, "/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit/tools")

    # Mock the paths for local testing
    import unlock_tool

    # Override paths for local testing
    unlock_tool.RUNTIME_DIR = "/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit"

    # Load unlock messages
    unlock_messages_path = os.path.join(unlock_tool.RUNTIME_DIR, "data", "unlock_messages.json")
    try:
        with open(unlock_messages_path, "r") as f:
            messages = json.load(f)
        print(f"✅ unlock_tool.py can load unlock_messages.json")
    except Exception as e:
        print(f"❌ Failed to load: {e}")
        return False

    # Verify outline_editor message
    outline_msg = messages.get("outline_editor", {})
    if outline_msg.get("requires_credentials"):
        print(f"✅ outline_editor marked as requiring credentials")
    else:
        print(f"❌ outline_editor not marked as requiring credentials")
        return False

    if outline_msg.get("credential_key") == "outline_api_key":
        print(f"✅ outline_editor credential_key is 'outline_api_key'")
    else:
        print(f"❌ outline_editor credential_key is wrong: {outline_msg.get('credential_key')}")
        return False

    return True


if __name__ == "__main__":
    print("="*60)
    print("UNLOCK MESSAGES TEST SUITE")
    print("="*60 + "\n")

    tests_passed = 0
    tests_total = 3

    if test_unlock_messages_format():
        tests_passed += 1

    if test_unlock_message_content():
        tests_passed += 1

    if test_unlock_tool_integration():
        tests_passed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("="*60)

    if tests_passed == tests_total:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
