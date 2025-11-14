import json
import sys
import argparse

SESSION_PATH = "session_state.json"

def set_mode(mode):
    with open(SESSION_PATH, "r") as f:
        session = json.load(f)
    session["mode"] = mode
    with open(SESSION_PATH, "w") as f:
        json.dump(session, f, indent=4)
    return {"status": "success", "message": f"✅ Mode set to '{mode}'."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--params")
    args = parser.parse_args()

    if args.action == "set_mode":
        params = json.loads(args.params)
        mode = params.get("mode", "json")
        result = set_mode(mode)
        print(json.dumps(result, indent=4))