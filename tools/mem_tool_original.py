#!/usr/bin/env python3
import os
import json
import argparse
import requests

# === CONFIG ===
# === CONFIG ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "tools", "credentials.json")
creds = json.load(open(CREDENTIALS_PATH))

API_BASE = "https://api.mem.ai/v2"
mem_api_key = creds["mem_api_key"]  # ✅ Matches scanner pattern + passes filter
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {mem_api_key}"
}


# === HELPERS ===
def handle_response(res):
    try:
        res.raise_for_status()
        return res.json()
    except requests.exceptions.HTTPError:
        return {"status": "error", "message": res.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# === TOOL ACTIONS ===
def create_note(params):
    payload = {
        "content": params.get("content")
    }
    return handle_response(requests.post(f"{API_BASE}/notes", headers=HEADERS, json=payload))

def read_note(params):
    note_id = params.get("note_id")
    return handle_response(requests.get(f"{API_BASE}/notes/{note_id}", headers=HEADERS))

def delete_note(params):
    note_id = params.get("note_id")
    return handle_response(requests.delete(f"{API_BASE}/notes/{note_id}", headers=HEADERS))

def mem_it(params):
    payload = {
        "input": params.get("input")
    }
    if params.get("instructions"):
        payload["instructions"] = params.get("instructions")
    return handle_response(requests.post(f"{API_BASE}/mem-it", headers=HEADERS, json=payload))

def create_collection(params):
    payload = {
        "title": params.get("title")
    }
    if params.get("description"):
        payload["description"] = params.get("description")
    return handle_response(requests.post(f"{API_BASE}/collections", headers=HEADERS, json=payload))

def delete_collection(params):
    cid = params.get("collection_id")
    return handle_response(requests.delete(f"{API_BASE}/collections/{cid}", headers=HEADERS))

def ping(_):
    return handle_response(requests.get(f"{API_BASE}/notes/bogus-id", headers=HEADERS))

# === CLI ENTRYPOINT ===
ACTIONS = {
    "create_note": create_note,
    "read_note": read_note,
    "delete_note": delete_note,
    "mem_it": mem_it,
    "create_collection": create_collection,
    "delete_collection": delete_collection,
    "ping": ping
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=list(ACTIONS.keys()))
    parser.add_argument("--params", type=str, default="{}")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = ACTIONS[args.action](params)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()
