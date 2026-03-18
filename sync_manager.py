import os
import json
import time

# config.json からフォルダIDを読み込み、assetsディレクトリの状態を playlist.js に反映する同期マネージャー

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def sync():
    config = load_config()
    folder_id = config.get('drive_folder_id', 'NOT_SET')
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Syncing from Google Drive Folder ID: {folder_id}")
    
    # ここに Google Drive API によるダウンロード処理の実装を追加します
    
    # 同期完了後、assets フォルダ内のファイル一覧を取得して playlist.js を更新
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
        
    files = [f for f in os.listdir(assets_dir) if os.path.isfile(os.path.join(assets_dir, f)) and not f.startswith('.')]
    
    playlist_content = f"const playlist = {json.dumps(files, indent=2, ensure_ascii=False)};"
    with open(os.path.join(os.path.dirname(__file__), 'playlist.js'), 'w', encoding='utf-8') as f:
        f.write(playlist_content)
    print(f"Playlist updated with {len(files)} files.")

if __name__ == "__main__":
    while True:
        try:
            sync()
        except Exception as e:
            print(f"Error during sync: {e}")
        time.sleep(300) # 5分ごとに同期を実行
