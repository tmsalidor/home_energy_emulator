# Windows (WSL2) + Docker で Wi-SUNドングルを利用する方法

Windows上のDocker Desktop (WSL2バックエンド) でUSBシリアルデバイス (Wi-SUNドングル) をコンテナに認識させるには、WindowsホストからWSL2へUSBデバイスをパススルーする必要があります。

これにはMicrosoftが提供するオープンソースツール **`usbipd-win`** を使用します。

## 1. 必要なツールのインストール (Windows側)

PowerShell (管理者権限) で以下のコマンドを実行し、`usbipd-win` をインストールします。

```powershell
winget install usbipd
```
※ インストール後、PCの再起動が必要な場合があります。

Linux (WSL2) 側にもUSB/IPツールが必要な場合があります（最新のUbuntu/WSL2では標準で入っていることが多いですが、なければ `apt install linux-tools-generic hwdata` 等でインストールします）。

## 2. USBドングルの接続と確認

Wi-SUNドングルをPCに接続し、PowerShellでデバイス一覧を表示します。

```powershell
usbipd list
```

出力例:
```text
BUSID  VID:PID    DEVICE                                                        STATE
2-1    10c4:ea60  Silicon Labs CP210x USB to UART Bridge (COM3)                 Not attached
...
```
ここで対象のドングルの **BUSID** (例: `2-1`) を確認してください。

## 3. WSL2へのアタッチ (Bind & Attach)

Windows側からWSL2へデバイスをアタッチします。

**初回のみ (バインド):**
```powershell
usbipd bind --busid 2-1
```
※ `2-1` は実際のBUSIDに置き換えてください。

**アタッチ (Docker起動前に毎回必要):**
```powershell
usbipd attach --wsl --busid 2-1
```
※ Docker Desktopが使用しているWSLディストリビューション（通常 `docker-desktop` または `Ubuntu` 等のデフォルトディストリなど）にアタッチされます。明示的に指定する場合は `--distribution Ubuntu-22.04` などを付けます。
※ **注意**: USBドングルをアタッチしている間、Windows側 (COMポート) からはアクセスできなくなります。

## 4. WSL2 インスタンス内での確認

WSL2のターミナル（Ubuntuなど）を開き、デバイスが認識されているか確認します。

```bash
lsusb
ls -l /dev/ttyUSB0
```
`/dev/ttyUSB0` (または USB1) が見えていれば成功です。

## 5. Docker Compose での実行

`docker-compose.yml` に以下のようにデバイスマッピングが記述されていることを確認します（修正済みです）。

```yaml
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
```

コンテナを起動します。

```bash
docker-compose up -d
```

これで、コンテナ内のアプリケーション (`/dev/ttyUSB0` を使用設定) からドングルにアクセスできるようになります。

## トラブルシューティング
- **権限エラー**: コンテナ内で `/dev/ttyUSB0` へのアクセス権がない場合、`privileged: true` を追加するか、ユーザーグループ設定が必要な場合がありますが、通常はrootで動くため問題ありません。
- **切断**: PCを再起動したりUSBを抜いた場合は、再度 `usbipd attach` コマンドを実行する必要があります。
