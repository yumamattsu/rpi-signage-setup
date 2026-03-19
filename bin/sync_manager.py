#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive Sync Manager for Digital Signage
- Uses Service Account for authentication.
- Checks for updates in a specific Drive Folder.
- Synchronizes files (Download new/changed, Delete missing).
"""
import os
import sys
import time
import shutil
import logging
import hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
# --- Configuration ---
BASE_DIR = "/home/pi/signage"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials/service_account.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "sync.log")
CACHE_DIR = "/home/pi/.cache/chromium"
# Drive Folder ID to sync (Replace with actual ID)
# ユーザーが後で書き換える必要がある場所
DRIVE_FOLDER_ID = "14nRlg8DDFV3VRMT9OLZx96r7Ciq4pOf4"
# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
# --- Logging Setup ---
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)
def get_service():
    """Authenticates and returns the Drive service."""
    if not os.path.exists(CREDENTIALS_FILE):
        logging.error(f"Credentials file not found: {CREDENTIALS_FILE}")
        sys.exit(1)
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Failed to create Drive service: {e}")
        sys.exit(1)
def get_remote_files(service, folder_id):
    """Lists files in the Drive folder."""
    files_dict = {}
    page_token = None
    try:
        while True:
            # Query: valid file, not trashed, inside folder
            q = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
            results = service.files().list(
                q=q,
                pageSize=100,
                fields="nextPageToken, files(id, name, md5Checksum, modifiedTime)",
                pageToken=page_token
            ).execute()
            items = results.get('files', [])
            for item in items:
                files_dict[item['name']] = item
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        return files_dict
    except HttpError as error:
        logging.error(f"An error occurred during list: {error}")
        return None
def download_file(service, file_id, file_path):
    """Downloads a single file."""
    try:
        request = service.files().get_media(fileId=file_id)
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        logging.info(f"Downloaded: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to download {file_id}: {e}")
        return False
def clear_browser_cache():
    """Clears Chromium cache to safely reflect new content."""
    if os.path.exists(CACHE_DIR):
        try:
            shutil.rmtree(CACHE_DIR)
            os.makedirs(CACHE_DIR)
            logging.info("Browser cache cleared.")
        except Exception as e:
            logging.error(f"Failed to clear cache: {e}")
def main():
    logging.info("--- Sync Started ---")
    if DRIVE_FOLDER_ID == "REPLACE_WITH_YOUR_DRIVE_FOLDER_ID":
        logging.error("Please configure DRIVE_FOLDER_ID in the script.")
        print("Error: DRIVE_FOLDER_ID is not set in sync_manager.py")
        sys.exit(1)
    service = get_service()
    
    # 1. Get Remote State
    remote_files = get_remote_files(service, DRIVE_FOLDER_ID)
    if remote_files is None:
        logging.error("Could not fetch remote files. Aborting.")
        sys.exit(1)
    
    # 2. Get Local State
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
    
    local_files = os.listdir(ASSETS_DIR)
    
    # Logic:
    # - Identify new/modified files (by name mainly, simplified for signage)
    # - Identify deleted files
    
    needs_update = False
    
    # Check for downloads
    for name, metadata in remote_files.items():
        file_path = os.path.join(ASSETS_DIR, name)
        should_download = False
        
        if name not in local_files:
            logging.info(f"New file found: {name}")
            should_download = True
        else:
            # Simple check: size or just overwrite? 
            # For strict sync, we can check MD5 if available (Drive provides md5Checksum for binary files)
            # If Google Doc/Sheet, no md5. Assuming binary assets (img/video).
            if 'md5Checksum' in metadata:
                # Calculate local MD5
                with open(file_path, 'rb') as f:
                    local_md5 = hashlib.md5(f.read()).hexdigest()
                if local_md5 != metadata['md5Checksum']:
                    logging.info(f"Modified file found: {name}")
                    should_download = True
            else:
                # Check modifiedTime if MD5 missing? Or just skip logic for non-binaries for now.
                pass
        if should_download:
            needs_update = True
            download_file(service, metadata['id'], file_path)
    # Check for deletions
    for name in local_files:
        if name not in remote_files:
            file_path = os.path.join(ASSETS_DIR, name)
            # Skip playlist.js, config.json, qr_code.svg, company_logo.png and internal files
            if name in ["playlist.js", "config.json", "qr_code.svg", "company_logo.png"] or name.startswith("."):
                continue
                
            try:
                os.remove(file_path)
                logging.info(f"Deleted local file: {name}")
                needs_update = True
            except Exception as e:
                logging.error(f"Failed to delete {file_path}: {e}")
    # 4. Always generate playlist (to ensure it exists and is up to date)
    generate_playlist()
    # 5. Post-Sync Action
    if needs_update:
        logging.info("Updates detected. Playlist regenerated.")
        # clear_browser_cache() # Not strictly needed for local file access but good for cleanup
    else:
        logging.info("No changes detected.")
def generate_playlist():
    """Generates a JavaScript file defining the playlist from assets."""
    try:
        # Filter for valid image/video/pdf extensions
        valid_exts = ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.pdf')
        excluded_files = ["playlist.js", "config.json", "qr_code.svg", "company_logo.png", "company_logo.png"]
        
        files = [f for f in os.listdir(ASSETS_DIR) 
                 if f.lower().endswith(valid_exts) and f not in excluded_files and not f.startswith(".")]
        files.sort() # Alphabetical order
        
        js_content = f"const playlist = {files};\n"
        
        playlist_path = os.path.join(BASE_DIR, "player", "playlist.js")
        # Ensure player dir exists
        player_dir = os.path.dirname(playlist_path)
        if not os.path.exists(player_dir):
            os.makedirs(player_dir)
        with open(playlist_path, 'w') as f:
            f.write(js_content)
        logging.info(f"Generated playlist.js with {len(files)} items.")
    except Exception as e:
        logging.error(f"Failed to generate playlist: {e}")
    logging.info("--- Sync Completed ---")
if __name__ == '__main__':
    main()