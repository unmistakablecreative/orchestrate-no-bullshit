
import os
import subprocess


# --- Core Functions ---

def run_terminal_command(command):
    import subprocess
    
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        return {"status": "success", "output": result}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.output.strip()}

def run_script_file(path):
    import subprocess
    import os
    
    if not os.path.exists(path):
        return {"status": "error", "message": f"❌ File not found: {path}"}
    
    try:
        result = subprocess.check_output(path, shell=True, stderr=subprocess.STDOUT, text=True)
        return {"status": "success", "output": result}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.output.strip()}

def stream_terminal_output(command):
    import subprocess
    
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = ""
    for line in process.stdout:
        output += line
    process.wait()
    
    return {"status": "success", "output": output.strip()}

def sanitize_command(command):
    dangerous = ["rm -rf", "shutdown", "reboot", ":(){:|:&};:", "mkfs"]
    
    if any(d in command for d in dangerous):
        return {"status": "error", "message": "❌ Unsafe command blocked."}
    
    return {"status": "success", "message": "✅ Command is safe."}

def get_last_n_lines_of_output(command, n):
    import subprocess
    
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        lines = output.strip().splitlines()
        return {"status": "success", "output": "\n".join(lines[-int(n):])}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.output.strip()}

def list_directory_contents(path):
    import os
    
    if not os.path.exists(path):
        return {"status": "error", "message": f"❌ Path not found: {path}"}
    
    try:
        items = os.listdir(path)
        return {"status": "success", "items": items}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# --- Action Router ---
if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--params")
    args = parser.parse_args()
    params = json.loads(args.params) if args.params else {}

    if args.action == "run_terminal_command":
        result = run_terminal_command(**params)
    elif args.action == "script":
        result = run_script_file(**params)
    elif args.action == "stream":
        result = stream_terminal_output(**params)
    elif args.action == "check_safe":
        result = sanitize_command(**params)
    elif args.action == "tail":
        result = get_last_n_lines_of_output(**params)
    elif args.action == "ls":
        result = list_directory_contents(**params)
    else:
        result = {"status": "error", "message": f"Unknown action {args.action}"}

    print(json.dumps(result, indent=2))
