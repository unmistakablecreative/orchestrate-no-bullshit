import json
import os
import sys
import argparse
import requests
from datetime import datetime

def load_credentials():
    with open("tools/credentials.json", "r") as f:
        return json.load(f)

def get_headers():
    creds = load_credentials()
    return {
        "Content-Type": "application/json",
        "X-Kit-Api-Key": creds["CONVERTKIT_API_KEY"]
    }



def create_broadcast(params):
    url = "https://api.kit.com/v4/broadcasts"
    now_iso = datetime.utcnow().isoformat() + "Z"
    payload = {
        "subject": params["subject"],
        "content": params["content"],
        "description": params["description"],
        "preview_text": params["preview_text"],
        "public": params.get("public", True),
        "published_at": now_iso,
        "send_at": params.get("send_at"),
        "email_template_id": params.get("email_template_id"),  # 👈 no default
    }

    # Optional: add subscriber_filter if user specifies it
    if "subscriber_filter" in params:
        payload["subscriber_filter"] = params["subscriber_filter"]

    response = requests.post(url, headers=get_headers(), json=payload)
    return response.json()


def get_broadcast(params):
    url = f"https://api.kit.com/v4/broadcasts/{params['id']}"
    response = requests.get(url, headers=get_headers())
    return response.json()


def update_broadcast(params):
    url = f"https://api.kit.com/v4/broadcasts/{params['id']}"
    now_iso = datetime.utcnow().isoformat() + "Z"
    payload = {
        "subject": params["subject"],
        "content": params["content"],
        "description": params["description"],
        "preview_text": params["preview_text"],
        "public": params.get("public", True),
        "published_at": now_iso,
        "send_at": params.get("send_at"),
        "email_template_id": params.get("email_template_id")  # 👈 pulled from params
    }

    # Optional: subscriber filter (if user wants to change audience)
    if "subscriber_filter" in params:
        payload["subscriber_filter"] = params["subscriber_filter"]

    response = requests.put(url, headers=get_headers(), json=payload)
    return response.json()


def list_broadcasts(params):
    url = "https://api.kit.com/v4/broadcasts"
    response = requests.get(url, headers=get_headers(), params=params)
    return response.json()

def get_current_account(params):
    url = "https://api.kit.com/v4/account"
    response = requests.get(url, headers=get_headers())
    return response.json()

def get_email_stats(params):
    url = "https://api.kit.com/v4/account/email_stats"
    response = requests.get(url, headers=get_headers())
    return response.json()

def get_growth_stats(params):
    url = "https://api.kit.com/v4/account/growth_stats"
    response = requests.get(url, headers=get_headers(), params=params)
    return response.json()

def get_broadcast_stats(params):
    url = f"https://api.kit.com/v4/broadcasts/{params['broadcast_id']}/stats"
    response = requests.get(url, headers=get_headers())
    return response.json()

def create_subscriber(params):
    url = "https://api.kit.com/v4/subscribers"
    payload = {
        "first_name": params.get("first_name"),
        "email_address": params["email_address"],
        "state": "active",
        "fields": params.get("fields", {})
    }
    response = requests.post(url, headers=get_headers(), json=payload)
    return response.json()



# Action registry for execution_hub
ACTIONS = {
        "create_broadcast": create_broadcast,
        "get_broadcast": get_broadcast,
        "update_broadcast": update_broadcast,
        "list_broadcasts": list_broadcasts,
        "get_current_account": get_current_account,
        "get_email_stats": get_email_stats,
        "get_growth_stats": get_growth_stats,
        "create_subscriber": create_subscriber,
        "get_broadcast_stats": get_broadcast_stats  # 🆕 Added
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--params", type=str)
    args = parser.parse_args()

    action_map = {
        "create_broadcast": create_broadcast,
        "get_broadcast": get_broadcast,
        "update_broadcast": update_broadcast,
        "list_broadcasts": list_broadcasts,
        "get_current_account": get_current_account,
        "get_email_stats": get_email_stats,
        "get_growth_stats": get_growth_stats,
        "create_subscriber": create_subscriber,
        "get_broadcast_stats": get_broadcast_stats  # 🆕 Added
    }

    try:
        params = json.loads(args.params or "{}")
        if args.action not in action_map:
            raise ValueError("Unsupported action")
        result = action_map[args.action](params)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()