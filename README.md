# HEMS IoT Emulator with ECHONET Lite

ECHONET Liteプロトコルに対応したHEMS (Home Energy Management System) エミュレーターです。
スマートメーター (Bルート対応)、太陽光発電システム、蓄電池システムをエミュレートし、NiceGUIによるWebインターフェースで状態監視・操作が可能です。

## 機能
- **スマートメーター**: Wi-SUN (Bルート) 経由でのプロパティ公開、瞬時電力・積算電力量のシミュレーション。
- **太陽光発電・蓄電池**: Wi-Fi (UDP) 経由でのECHONET Liteプロパティ公開、発電量・SOCのシミュレーション。
- **Web UI**: 各デバイスの状態監視、デバッグ用パラメータの手動操作。

## 必要ハードウェア
- **Wi-SUN USBドングル**: ローム社製 BP35A1 等（Bルート通信用）
- **Linux PC**: Ubuntu 推奨 (WindowsでのDocker実行はネットワーク制限により推奨されません)

## セットアップ手順 (Linux / Ubuntu)

本システムを別のLinuxマシンに移植して実行する手順です。

### 1. ファイルの配置
プロジェクトディレクトリ一式を対象のマシンにコピーしてください。

### 2. Wi-SUNドングルの接続
USBドングルをPCに接続し、デバイスパスを確認してください（通常 `/dev/ttyUSB0`）。
必要に応じて権限を付与してください：
```bash
sudo chmod 666 /dev/ttyUSB0
```

### 3. Docker設定の確認 (重要)
`docker-compose.yml` を編集し、**ホストネットワークモード**が有効になっていることを確認してください。
ECHONET Liteの機器探索（マルチキャスト通信）を正常に動作させるために必須です。

```yaml
services:
  app:
    # ports: ... (hostモード時は無視されます)
    network_mode: "host"  # <-- この行が有効(コメントアウトされていない)であることを確認
    # ...
```

### 4. 起動
以下のコマンドでコンテナをビルド・起動します。

```bash
docker-compose up --build
```

### 5. アクセス
同じネットワーク内のPCからブラウザでアクセスします。

URL: `http://<LinuxマシンのIPアドレス>:8080`

## Windows環境での実行について
Windows版Docker Desktopでは、ネットワーク構成の制限によりECHONET Liteのマルチキャストパケットが通過しない場合があります。
Windowsで利用する場合は、Dockerを使用せず、Python環境をホストに直接インストールして実行することを推奨します。

```powershell
pip install -r requirements.txt
# 設定ファイル(config/user_settings.yaml)でCOMポートを指定後に実行:
python src/main.py
```
