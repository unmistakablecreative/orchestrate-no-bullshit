import os
import subprocess
import json
import argparse
from typing import List

# === Load GitHub token ===
CREDENTIAL_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")

def load_credential(key):
    try:
        with open(CREDENTIAL_PATH, "r") as f:
            return json.load(f).get(key)
    except Exception:
        return None

GITHUB_TOKEN = load_credential("github_access_token")

# === Helper Functions ===

def run_git(command: List[str], path: str):
    try:
        result = subprocess.run(command, cwd=path, capture_output=True, text=True, check=True)
        return {"status": "success", "output": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": e.stderr.strip() or str(e),
            "command": " ".join(command)
        }

def ensure_git_identity(path: str):
    subprocess.run(["git", "config", "user.name", "unmistakablecreative"], cwd=path)
    subprocess.run(["git", "config", "user.email", "srini@unmistakablemedia.com"], cwd=path)

# === Git Actions ===

def clone_repo(url, path):
    return run_git(["git", "clone", url, path], ".")

def init_repo(path):
    os.makedirs(path, exist_ok=True)
    result = run_git(["git", "init"], path)
    ensure_git_identity(path)
    return result

def set_remote(path, url):
    return run_git(["git", "remote", "add", "origin", url], path)

def add_files(path, files: List[str]):
    return run_git(["git", "add"] + files, path)

def commit_repo(path, message):
    ensure_git_identity(path)
    return run_git(["git", "commit", "-m", message], path)

def push_repo(path, branch="main"):
    ensure_git_identity(path)

    # Ensure main branch exists
    branch_check = run_git(["git", "rev-parse", "--verify", branch], path)
    if branch_check["status"] == "error":
        created = run_git(["git", "checkout", "-b", branch], path)
        if created["status"] != "success":
            return created

    # Patch token into remote
    patched = patch_remote_token(path)
    if patched["status"] != "success":
        return patched

    return run_git(["git", "push", "-u", "origin", branch], path)

def pull_repo(path, branch="main"):
    return run_git(["git", "pull", "origin", branch], path)

def patch_remote_token(path):
    if not GITHUB_TOKEN:
        return {"status": "error", "message": "❌ GitHub token not found."}
    try:
        result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=path, capture_output=True, text=True, check=True)
        url = result.stdout.strip()
        if "@" not in url:
            authed = url.replace("https://", f"https://{GITHUB_TOKEN}@")
            subprocess.run(["git", "remote", "set-url", "origin", authed], cwd=path)
        return {"status": "success"}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": f"❌ Failed to patch token: {str(e)}"}

def list_repos(root="./projects"):
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=dirpath, capture_output=True, text=True)
            entries.append({
                "name": os.path.basename(dirpath),
                "path": dirpath,
                "branch": branch.stdout.strip() if branch.returncode == 0 else "unknown"
            })
            dirnames[:] = []  # Avoid recursion
    return {"status": "success", "repos": entries}

# === Dispatcher ===

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--params")
    args = parser.parse_args()
    params = json.loads(args.params) if args.params else {}

    actions = {
        "clone_repo": clone_repo,
        "init_repo": init_repo,
        "set_remote": set_remote,
        "add_files": add_files,
        "commit_repo": commit_repo,
        "push_repo": push_repo,
        "pull_repo": pull_repo,
        "list_repos": list_repos
    }

    func = actions.get(args.action)
    if not func:
        result = {"status": "error", "message": f"❌ Unknown action: {args.action}"}
    else:
        try:
            result = func(**params)
        except Exception as e:
            result = {"status": "error", "message": f"Exception: {str(e)}"}

    print(json.dumps(result, indent=2))
