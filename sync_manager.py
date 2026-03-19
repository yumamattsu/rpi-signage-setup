import os
import json
import time
import sys
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload

# config.json からフォルダIDを読み込み、Google Drive から assets フォルダへ同期するマネージャー

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials/service_account.json')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_service():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def sync():
    config = load_config()
    folder_id = config.get('drive_folder_id')
    if not folder_id or folder_id == "GOOGLE_DRIVE_FOLDER_ID":
        print("Wait: Google Drive Folder ID is not set in config.json")
        return

    service = get_service()
    if not service:
        print("Wait: Credentials file not found at " + CREDENTIALS_FILE)
        # 認証ファイルがない場合は、ローカルにあるファイルだけでプレイリストを更新する
        update_playlist([])
        return

    try:
        # フォルダ内のファイル一覧を取得
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, md5Checksum)"
        ).execute()
        items = results.get('files', [])

        if not os.path.exists(ASSETS_DIR):
            os.makedirs(ASSETS_DIR)

        remote_names = []
        for item in items:
            name = item['name']
            remote_names.append(name)
            file_path = os.path.join(ASSETS_DIR, name)
            
            # 簡易的な上書きチェック（本来はMD5等で比較すべきですが、ここでは存在確認のみ）
            if not os.path.exists(file_path):
                print(f"Downloading: {name}")
                request = service.files().get_media(fileId=item['id'])
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
        
        # 削除されたファイルのクリーンアップ（任意ですが、ここではプレイリスト更新のみ）
        update_playlist(remote_names)

    except Exception as e:
        print(f"Sync Error: {e}")

def update_playlist(remote_names):
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
        
    excluded = ['company_logo.png', 'qr_code.svg', 'playlist.js', 'config.json']
    files = [f for f in os.listdir(ASSETS_DIR) 
             if os.path.isfile(os.path.join(ASSETS_DIR, f)) 
             and not f.startswith('.') 
             and f not in excluded]
    files.sort()
    
    playlist_content = f"const playlist = {json.dumps(files, indent=2, ensure_ascii=False)};"
    with open(os.path.join(os.path.dirname(__file__), 'playlist.js'), 'w', encoding='utf-8') as f:
        f.write(playlist_content)
    print(f"Playlist updated: {len(files)} files.")

if __name__ == "__main__":
    while True:
        sync()
        time.sleep(300) # 5分おきにチェック
