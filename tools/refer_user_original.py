import os
import sys
import json
import requests
import shutil
import argparse
from zipfile import ZipFile
from datetime import datetime

# === CONTAINER PATHS (Docker environment) ===
CREDENTIALS_PATH = "/container_state/system_identity.json"
SECONDBRAIN_PATH = "/opt/orchestrate-core-runtime/data/secondbrain.json"
USER_MOUNT_DIR = "/orchestrate_user"
RUNTIME_DIR = "/opt/orchestrate-core-runtime"

# === DMG CONFIG ===
DMG_FILENAME = "orchestrate_engine_final.dmg"
DMG_SOURCE_PATH = os.path.join(RUNTIME_DIR, DMG_FILENAME)
DMG_GITHUB_URL = "https://github.com/unmistakablecreative/orchestrate-core-runtime/raw/main/orchestrate_engine_final.dmg"

# === DROPBOX CONFIG ===
DROPBOX_APP_KEY = "t6as3o0q6oyj5ut"
DROPBOX_APP_SECRET = "e8qbf60g23gxec2"
DROPBOX_REFRESH_TOKEN = "1tRiwqZsTZ4AAAAAAAAAAfc27_wasvuLOTD7SzoBfLrcRL7srZm4tEnGc8NTysRG"

# Current access token (will be refreshed automatically)
DROPBOX_ACCESS_TOKEN = "sl.u.AF_mKkX5jtEBvANUVWjP1IDVPlTd7jXYZZ6pnQh0y2qAqvE1ySqGlp5TLp1onbCOotCB-hOT8kWR0nQpXyAtG9QAtRCOdApE5KWEzRg9yiRM5GOUTBtuSm8flzDyXgvL2NxgRqJ06yJsivFQcafphGUKeM65PRfq-7YlhcheYK7_bNEaJMwXQK1RLSPRo3swVpXPaTseuQa3GbVkSdY2ejYqRXXEXl5X_C8Le_p7igzyNNB6Y3kyxEMD2ykrHMR72qsN5EiutLYyYAwfAsrMP1VZ9EtP5hRUAONNXZVSNRq8RbOWQSa-F2LEGsVradWpmRzVLWex8DIcBJvV81I59XSZweUIEuleWH0LuHA-pmMchZK0gyhzBXbZd6IBefzqDk7mWuSbDiVqrLA-BEnwOOgK4yCNc0a0_H0hyPCsoIZUrPYPhieAwYkUIcPihDCWIYZ2bWs5Do0fp3Jq5v_j4GuD5-3Ni1_fboHN7r0GGS1UaQpbN_Y0DB0SkQgNEiNmFbnYf2bHuaA_CgT2tLhbduq4J-1jeibYrLjyUhySBtIsjTcyxK0GkjC7KJkykIkr6xkfk7zWSSZJsWSpW8E46JxCWAsDE2SPgONdZ_pd6WwrtKWiOeT0CO0j3LBxgZV7KXjinc1Kd0NOwouHqXN2c6shbpOWyU3nPr9h2MwG5a5jQVH2-_eB9Si9Pe0enIeM7UXYgJGcpRtueqX2Wb4RDy1NcllBz4ZY1UmCEJFhJubSBu0VCOwtR8FHEq0z8_vkqNhTOONcn0mHNtbXtee_eAxRC-gJkMCi610iHIJvE_LT1ii3Vq94K5wjvGdt-srX-NouYhtP4KE8L30XxtJU16D7PSZJ9ApGIcHwoGSv-WEYYT5vi6o1LE7RnqO9vPpSaVKG_dQV5wdBtC5mw1QSo_SUW7Q8uF9w70I5mxz8KajstxkwtKJwZ4ilj9Hc1xGu7ZyvD6LBgyascD2J2bntaoWQYXBZl-_uWGdtEupn2rsqA5tQ1TtjvlpNPHuNoXU5Lk-rsJyKHgoZMXV314Ndk0vk_j5noypYrO4WvGamKAyrC1GhB5XtinHES539n_jfc8s5VyqjDUM2gHJbytLvBEd2wvL0ogL1rtJOd5OkydeMXbAOYY-GcrIbII65HjzjDtUJxZ2ZQcl6ydYfMSD2MpQMZA38lTYQTrouo00TdJGLjLLTU2l_22nvmxp8vV3rTB02xoK-PHF6cJZ-oqL1iV7cWhQkpKmf2ZPdL8c5z3dQYM2GpmZ8aIOOutLaE1kPUOc2dM5Yd1wPvLxxsPU1Qh4k"

# === AIRTABLE CONFIG ===
AIRTABLE_API_KEY = "patyuDyrmZz0s6bLO.7e4f3c3ca7f3a4be93d9d4f3b57c2635fd0aab5dce43bb1de2aa37ceeeda886d"
AIRTABLE_BASE_ID = "appoNbgV6oY603cjb"
AIRTABLE_TABLE_ID = "tblpa06yXMKwflL7m"

def refresh_dropbox_token():
    """Get a new access token using the refresh token"""
    try:
        print("DEBUG: Refreshing Dropbox access token...")
        
        url = "https://api.dropbox.com/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": DROPBOX_REFRESH_TOKEN,
            "client_id": DROPBOX_APP_KEY,
            "client_secret": DROPBOX_APP_SECRET
        }
        
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        new_access_token = token_data["access_token"]
        
        print("DEBUG: Dropbox token refreshed successfully")
        return new_access_token
        
    except Exception as e:
        raise Exception(f"Failed to refresh Dropbox token: {str(e)}")

def get_valid_dropbox_token():
    """Get a valid Dropbox access token, refreshing if necessary"""
    global DROPBOX_ACCESS_TOKEN
    
    # Try current token first
    test_url = "https://api.dropboxapi.com/2/users/get_current_account"
    headers = {"Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}"}
    
    try:
        response = requests.post(test_url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("DEBUG: Current Dropbox token is valid")
            return DROPBOX_ACCESS_TOKEN
    except:
        pass
    
    # Token expired or invalid, refresh it
    print("DEBUG: Current token invalid, refreshing...")
    DROPBOX_ACCESS_TOKEN = refresh_dropbox_token()
    return DROPBOX_ACCESS_TOKEN

def ensure_dmg_exists():
    """Download DMG from GitHub if it doesn't exist locally"""
    if os.path.exists(DMG_SOURCE_PATH):
        print("DEBUG: DMG found locally")
        return True
    
    print("DEBUG: DMG not found locally, downloading from GitHub...")
    
    try:
        response = requests.get(DMG_GITHUB_URL, stream=True, timeout=120)
        response.raise_for_status()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DMG_SOURCE_PATH), exist_ok=True)
        
        # Download with progress
        with open(DMG_SOURCE_PATH, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"DEBUG: DMG downloaded successfully to {DMG_SOURCE_PATH}")
        return True
        
    except Exception as e:
        raise Exception(f"Failed to download DMG: {str(e)}")

def upload_to_dropbox(file_path, dropbox_path):
    """Upload file to Dropbox and return download URL"""
    try:
        # Get a valid access token
        access_token = get_valid_dropbox_token()
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"DEBUG: Uploading {len(file_content)} bytes to Dropbox: {dropbox_path}")
        
        # Upload to Dropbox
        upload_url = "https://content.dropboxapi.com/2/files/upload"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps({
                "path": dropbox_path,
                "mode": "overwrite"
            })
        }
        
        response = requests.post(upload_url, headers=headers, data=file_content, timeout=120)
        response.raise_for_status()
        
        print("DEBUG: Dropbox upload successful")
        
        # Create shareable link
        share_url = "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings"
        share_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        share_data = {
            "path": dropbox_path,
            "settings": {
                "requested_visibility": "public"
            }
        }
        
        print("DEBUG: Creating Dropbox share link...")
        share_response = requests.post(share_url, headers=share_headers, json=share_data, timeout=30)
        
        if share_response.status_code == 200:
            share_result = share_response.json()
            # Convert share URL to direct download URL
            share_link = share_result["url"]
            download_url = share_link.replace("dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
            print(f"DEBUG: Dropbox download URL: {download_url}")
            return download_url
        else:
            print(f"DEBUG: Share link creation failed: {share_response.text}")
            # Try to handle existing link case
            if "shared_link_already_exists" in share_response.text:
                print("DEBUG: Share link already exists, trying to get existing link...")
                # Get existing links
                list_url = "https://api.dropboxapi.com/2/sharing/list_shared_links"
                list_data = {"path": dropbox_path}
                list_response = requests.post(list_url, headers=share_headers, json=list_data, timeout=30)
                if list_response.status_code == 200:
                    links = list_response.json().get("links", [])
                    if links:
                        existing_link = links[0]["url"]
                        download_url = existing_link.replace("dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
                        print(f"DEBUG: Using existing Dropbox URL: {download_url}")
                        return download_url
            
            # Fallback - return a constructed URL
            return f"https://dl.dropboxusercontent.com/s/placeholder{dropbox_path}"
            
    except Exception as e:
        raise Exception(f"Dropbox upload failed: {str(e)}")

def refer_user(params):
    try:
        name = params.get("name")
        email = params.get("email")
        
        if not name or not email:
            return {"status": "error", "message": "Missing name or email"}
        
        # Debug environment info
        debug_info = {
            "credentials_exists": os.path.exists(CREDENTIALS_PATH),
            "user_mount_exists": os.path.exists(USER_MOUNT_DIR),
            "runtime_dir_exists": os.path.exists(RUNTIME_DIR),
            "working_dir": os.getcwd()
        }
        print(f"DEBUG INFO: {json.dumps(debug_info, indent=2)}")
        
        # Check required paths
        if not os.path.exists(CREDENTIALS_PATH):
            return {
                "status": "error", 
                "message": f"Credentials file not found: {CREDENTIALS_PATH}"
            }
        
        # Ensure DMG exists (download if needed)
        try:
            ensure_dmg_exists()
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to ensure DMG exists: {str(e)}"
            }
        
        # Load user identity
        try:
            with open(CREDENTIALS_PATH, 'r') as f:
                identity = json.load(f)
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to read credentials: {str(e)}"
            }
        
        referrer_id = identity.get("user_id")
        if not referrer_id:
            return {
                "status": "error", 
                "message": "No user_id found in system_identity.json"
            }
        
        print(f"DEBUG: Found referrer_id: {referrer_id}")
        
        # Load referrer name from secondbrain (optional)
        referrer_name = "Unknown Referrer"
        if os.path.exists(SECONDBRAIN_PATH):
            try:
                with open(SECONDBRAIN_PATH, 'r') as f:
                    brain = json.load(f)
                referrer_name = brain.get("entries", {}).get("user_profile", {}).get("full_name", "Unknown Referrer")
            except Exception as e:
                print(f"DEBUG: Secondbrain read failed: {str(e)}")
        
        print(f"DEBUG: Using referrer_name: {referrer_name}")
        
        # === Create referral package ===
        safe_name = name.lower().replace(" ", "_").replace(".", "_")
        zip_name = f"Orchestrate_Installer_for_{safe_name}.zip"
        temp_build_dir = f"/tmp/referral_build_{safe_name}"
        zip_path = os.path.join(temp_build_dir, zip_name)
        
        print(f"DEBUG: Creating package {zip_name}")
        
        # Clean up any existing temp directory
        if os.path.exists(temp_build_dir):
            shutil.rmtree(temp_build_dir)
        os.makedirs(temp_build_dir, exist_ok=True)
        
        try:
            # Copy DMG to temp directory
            print("DEBUG: Copying DMG file...")
            dmg_temp_path = os.path.join(temp_build_dir, DMG_FILENAME)
            shutil.copy2(DMG_SOURCE_PATH, dmg_temp_path)
            
            # Create referrer file
            print("DEBUG: Creating referrer.txt...")
            referrer_temp_path = os.path.join(temp_build_dir, "referrer.txt")
            with open(referrer_temp_path, "w") as f:
                f.write(referrer_id)
            
            # Create ZIP package
            print("DEBUG: Creating ZIP package...")
            with ZipFile(zip_path, 'w') as zipf:
                zipf.write(dmg_temp_path, DMG_FILENAME)
                zipf.write(referrer_temp_path, "referrer.txt")
            
            print(f"DEBUG: ZIP package created successfully at {zip_path}")
            print(f"DEBUG: ZIP file size: {os.path.getsize(zip_path)} bytes")
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to create referral package: {str(e)}"
            }
        
        # === Upload to Dropbox ===
        try:
            dropbox_path = f"/referrals/{zip_name}"
            download_url = upload_to_dropbox(zip_path, dropbox_path)
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to upload to Dropbox: {str(e)}"
            }
        finally:
            # Clean up temp directory
            if os.path.exists(temp_build_dir):
                shutil.rmtree(temp_build_dir)
                print("DEBUG: Cleaned up temp directory")
        
        # === Submit to Airtable ===
        print("DEBUG: Submitting to Airtable...")
        airtable_data = {
            "fields": {
                "referrer_id": referrer_id,
                "referrer_name": referrer_name,
                "recipient_name": name,
                "recipient_email": email,
                "zip_url": download_url
            }
        }
        
        airtable_headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        airtable_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
        
        try:
            response = requests.post(airtable_url, headers=airtable_headers, json=airtable_data, timeout=30)
            response.raise_for_status()
            print("DEBUG: Airtable submission successful")
        except requests.exceptions.RequestException as e:
            return {
                "status": "error", 
                "message": f"Failed to submit to Airtable: {str(e)}"
            }
        
        return {
            "status": "success",
            "message": f"Referral package created for {name} ({email})",
            "download_url": download_url,
            "referrer_id": referrer_id,
            "referrer_name": referrer_name
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "traceback": traceback.format_exc()
        }

# === CLI Interface ===
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Create referral packages for OrchestrateEngine")
        parser.add_argument("action", help="Action to perform (refer_user)")
        parser.add_argument("--params", required=True, help="JSON parameters with name and email")
        
        args = parser.parse_args()
        
        print(f"DEBUG: Starting with action={args.action}")
        print(f"DEBUG: Params={args.params}")
        
        if args.action == "refer_user":
            params = json.loads(args.params)
            print(f"DEBUG: Parsed params: {params}")
            result = refer_user(params)
        else:
            result = {"status": "error", "message": f"Unknown action: {args.action}"}
            
    except json.JSONDecodeError as e:
        result = {"status": "error", "message": f"Invalid JSON parameters: {str(e)}"}
    except Exception as e:
        import traceback
        result = {
            "status": "error", 
            "message": f"Script initialization error: {str(e)}",
            "traceback": traceback.format_exc()
        }
    
    # Always ensure we output JSON
    try:
        print(json.dumps(result, indent=2))
        sys.stdout.flush()
    except Exception as e:
        print(f'{{"status": "error", "message": "JSON output failed: {str(e)}"}}')
        sys.stdout.flush()
