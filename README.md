# サイネージシステム 完全構築マスターガイド (Google Drive連携版)

これまでに構築したデジタルサイネージシステムの**全貌と全ての構築ステップ**をまとめた総合マニュアルです。
本ドキュメントおよび必要なシステムファイル一式（HTML, Pythonスクリプト, 認証キーなど）は**Google Drive上で一元管理**されています。
新しい拠点やラズパイを追加する際は、この手順書に従ってセットアップを行ってください。

---

## 全体像（システムの仕組み）

1. **画面表示（ラズパイ）**: `player.html` が表示を担当します。自動でフルスクリーンになり、天気を取得し、画像をスライドショーします。
2. **自動同期（ラズパイ）**: `sync_manager.py` が10分おきに動き、Google Drive上の特定フォルダから最新の画像や設定ファイルをラズパイ内にダウンロードします。
3. **設定変更（スマホ/PC）**: Google Apps Script (GAS) のWebアプリから、誰でも表示テキストなどを変更できます。

---

## フェーズ 1: クラウド・裏側の準備 (Google)
※ 既にシステムが稼働中の場合は、このフェーズはスキップしてフェーズ2へ進んでください。

1. **GCPとGoogle Drive API**: GCPでプロジェクトを作り、Drive APIを有効化。サービスアカウント（`service_account.json`）を発行します。
2. **共有フォルダ**: Google Drive上にサイネージ用のフォルダを作り、上記サービスアカウントに「**編集者**」権限を付与します。フォルダのIDをメモします。
3. **GASアプリの設定**: 用意されたスクリプトをGASにデプロイし、フォルダIDを設定します。

---

## フェーズ 2: ラズパイの初期セットアップ

表示端末となるRaspberry PiのSDカードを準備します（PC作業）。

1. **FullPageOS の書き込み**
   * Raspberry Pi Imager を使い、SDカードに FullPageOS を「カスタムOS」として書き込みます。
   * **⚠️重要**: Imagerの歯車設定から、ホスト名を拠点ごとに変更してください（例：`signage-fujimi` 等）。これにより遠隔管理時の重複エラーを防ぎます。
   * ※ 有線LANを挿す場合はWi-Fi設定は不要です。

2. **起動設定ファイル (`fullpageos.txt`) の書き換え**
   * 書き込み直後のSDカード（`boot` ドライブ）を開き、`fullpageos.txt` をPCのメモ帳等で開きます。
   * 中身をすべて消し、以下の**1行だけ**にします。
     ```text
     file:///home/pi/signage/player/player.html
     ```

---

## フェーズ 3: デバイス内の環境構築とファイル転送

ラズパイにSDカードとLANケーブルを挿して起動し、PCからSSH接続（例: `ssh pi@signage-fujimi.local`）してからの手順です。

### ステップ 3-A: 基本設定と依存ライブラリ導入
```bash
# タイムゾーンを日本に設定
sudo timedatectl set-timezone Asia/Tokyo

# ファイル格納用フォルダの作成
mkdir -p ~/signage/bin ~/signage/player ~/signage/assets ~/signage/credentials ~/signage/logs

# 【超重要】FullPageOSのフリーズ回避パッチ
# （ローカルHTML表示時にブラウザが起動しないバグを防ぎます）
echo "disabled" | sudo tee /boot/firmware/check_for_httpd

# Python環境とGoogleAPIライブラリのインストール
sudo apt-get update
sudo apt-get install -y python3-pip
# ※ バージョン指定が必須です（oauth2clientがv4以上だと非対応エラーになるため）
pip3 install google-api-python-client oauth2client<4.0.0
```

### ステップ 3-B: ファイルの転送
Google Driveに格納されている以下のファイルをダウンロードし、MacからSCPコマンド等でラズパイに転送します。
※接続先のアドレス（例: `pi@signage-fujimi.local`）は環境に合わせて変更してください。

```bash
TARGET="pi@signage-fujimi.local"

# 1. 認証キー
scp service_account.json $TARGET:~/signage/credentials/

# 2. 同期スクリプト
scp sync_manager.py $TARGET:~/signage/bin/

# 3. プレイヤー画面とアセット類
scp player.html $TARGET:~/signage/player/
scp *:*.js $TARGET:~/signage/player/    # (初回起動用のplaylist.jsやconfig.jsonがあれば)
scp qr_code.svg $TARGET:~/signage/assets/
scp company_logo.png $TARGET:~/signage/assets/
```

### ステップ 3-C: 自動同期設定 (Cron)
```bash
crontab -e
```
一番下の行に以下を追記して保存します（10分ごとに変更をチェック）。
```text
*/10 * * * * /usr/bin/python3 /home/pi/signage/bin/sync_manager.py >> /home/pi/signage/logs/sync.log 2>&1
```

これでラズパイを再起動（`sudo reboot`）すれば、数分後には自動的にサイネージが立ち上がります。

---

## フェーズ 4: 遠隔メンテナンスの導入 (必須オプション)

現場に行かずに画面の状態確認や再起動を行えるようにします。

1. **Tailscale のインストール**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
   表示されるURLにアクセスしてログイン・承認します。以降は、 Tailscale経由の 固定IP または `ssh pi@signage-fujimi` でどこからでも繋がります。

2. **VNC の有効化 (画面ののぞき見用)**
   ```bash
   sudo raspi-config
   ```
   「3 Interface Options」→「I3 VNC」を「Yes」にします。
   これにより、PC等の VNC Viewer からラズパイの画面をそのまま確認できるようになります。
