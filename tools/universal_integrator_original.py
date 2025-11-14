import subprocess
import json

# --- Core Functions ---

def run_terminal_command(command):
    result = subprocess.getoutput(command)
    return {"status": "success", "output": result}

# --- Action Router ---
def main():
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--params")
    args = parser.parse_args()
    params = json.loads(args.params) if args.params else {}
    if args.action == "run_terminal_command":
        result = run_terminal_command(**params)
    else:
        result = {"status": "error", "message": f"Unknown action {args.action}"}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
