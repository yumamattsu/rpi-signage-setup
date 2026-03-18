#!/bin/bash

# サイネージシステム一括セットアップスクリプト

echo "Starting Signage System Setup..."

# 1. 依存パッケージのインストール
# システムに必要なソフト（Python, Nginx等）を自動でインストールします。
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx

# 2. Python 仮想環境の作成
# 実行に必要なライブラリを他のソフトと干渉しないように隔離してインストールします。
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# 3. サービスファイルの作成 (systemd)
# 「電源を入れたら自動でプログラムを動かす」ための設定ファイルを作成します。
echo "Registering services..."

# API Server Service (管理画面用のサーバー)
cat <<EOF | sudo tee /etc/systemd/system/sgn_server.service
[Unit]
Description=Signage Admin API Server
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/server.py
WorkingDirectory=$(pwd)
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

# Sync Manager Service (Google Driveとの同期用)
cat <<EOF | sudo tee /etc/systemd/system/sgn_sync.service
[Unit]
Description=Signage Content Sync Manager
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/sync_manager.py
WorkingDirectory=$(pwd)
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

# 4. サービスの有効化と起動
# 設定を反映させ、今すぐプログラムを動かし始めます。
sudo systemctl daemon-reload
sudo systemctl enable sgn_server
sudo systemctl enable sgn_sync
sudo systemctl start sgn_server
sudo systemctl start sgn_sync

echo "------------------------------------------------"
echo "Setup Complete!"
echo "Signage Admin is running at http://$(hostname -I | awk '{print $1}'):8000/admin.html"
echo "------------------------------------------------"
