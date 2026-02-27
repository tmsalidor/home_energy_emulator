# Home Energy Emulator with ECHONET Lite

<img width="1253" height="1516" alt="image" src="https://github.com/user-attachments/assets/fe78bbae-866a-495b-b314-df96fc29452c" />


ECHONET Liteプロパティに対応したHEMS (Home Energy Management System) 対応機器エミュレーターです。
スマートメーター (Bルート対応)、太陽光発電システム、蓄電池システム、電気自動車充放電器 (V2H)、電気給湯器、家庭用エアコンをエミュレートし、NiceGUIによるWebインターフェースで状態監視・操作が可能です。

## 特徴
- **ハイブリッド通信エミュレーション**:
    - **スマートメーター**: Wi-SUN (Bルート) 経由でのプロパティ公開。実際のUSBドングル (BP35A1等) または仮想COMポートを通じてシリアル通信を行います。
    - **その他デバイス**: Wi-Fi (LAN) 経由でのECHONET Liteプロパティ公開 (UDP/Multicast)。
- **Web UI (NiceGUI)**:
    - **Dashboard**: 各デバイスの発電・充放電状態や消費電力のリアルタイム監視と、スライダーによる手動シミュレーション操作。
    - **Settings**: Web画面上でのID設定やパラメータ変更。
    - **Inspector**: ECHONET Liteプロパティの内部値をリアルタイムで確認できるデバッグ機能。
    - **Version Information**: Gitのコミットハッシュと日時を画面下部に表示し、実行中のバージョンを即座に確認可能。
- **ECHONET Liteプロパティ対応**:
    - **スマートメーター**: 瞬時電力 (0xE7)、積算電力量 (0xE0, 0xE3) など。
    - **太陽光発電**: 瞬時発電電力 (0xE0)、積算発電量 (0xE1) など。
    - **蓄電池**: SOC残量 (0xE4), 蓄電残量Wh (0xE2), 運転モード (0xDA), 充放電電力 (0xD3), 充放電可能電力量 (0xA4, 0xA5), 積算充放電量 (0xA8, 0xA9) など。
    - **電気自動車充放電器 (V2H)**: 運転モード (0xDA), 瞬時充放電電力 (0xD3), SOC残量 (0xE4), 放電可能容量/残容量 (0xC0, 0xC2, 0xE2), 積算充放電量 (0xD6, 0xD8), 充放電電力設定値 (0xEB, 0xEC) など。
    - **電気給湯器**: 運転状態 (0x80)、沸き上げ自動設定 (0xB0)、沸き上げ中状態 (0xB2)、残湯量 (0xE1)、タンク容量 (0xE2)、風呂自動モード設定 (0xE3 - Set/Get対応)、昼間沸き増し設定 (0xC0 - Set/Get対応)。
    - **家庭用エアコン**: 運転状態 (0x80)、運転モード設定 (0xB0)、温度設定値 (0xB3)、風量設定 (0xA0)、節電動作設定 (0x8F)、瞬時消費電力計測値 (0x84)、積算消費電力量計測値 (0x85) など。

## 必要要件
- **ハードウェア**:
    - Wi-SUN USBドングル (ローム社製 BP35A1 等) - Bルート通信エミュレーション用
    - Raspberry Pi (3B+, 4B, 5 等) 推奨 - 常時稼働用サーバーとして適しています。
- **ソフトウェア環境**:
    - **推奨**: Linux (Ubuntu, Raspberry Pi OS) - Docker (`network_mode: host`) がネイティブ動作するため、ECHONET Liteのマルチキャスト通信に最適です。
    - **Windows**: Python直接実行を推奨 (Docker Desktop for Windowsはネットワーク制限によりマルチキャストが正しく機能しない場合があります)。

## セットアップと実行

### 1. 構成ファイル (オプション)
`config/user_settings.yaml` でデバイスIDやパラメータを事前定義できますが、初回起動後にWeb UIの[Settings]タブからも設定可能です。

### 2. 実行方法 (Linux / Docker 推奨)

プロジェクトルートで以下のコマンドを実行します。

1.  **Docker設定の確認**:
    `docker-compose.yml` を確認し、`network_mode: "host"` が有効であることを確認してください。

2.  **USBデバイスの権限**:
    Wi-SUNドングルのデバイスパス (例: `/dev/ttyUSB0`) の権限設定が必要な場合があります。
    ```bash
    sudo chmod 666 /dev/ttyUSB0
    ```
    ※再起動後も権限を維持するには、udevルールを作成することをお勧めします。

3.  **ビルドと起動**:
    ```bash
    docker compose up --build
    ```

### 3. Raspberry Pi等での常時稼働 (自動起動)

Raspberry PiなどのLinux端末で、電源投入時に自動的にエミュレーターを起動させたい場合（常時稼働）は、`docker-compose.yml` のrestartポリシーを変更します。

1.  **docker-compose.yml の編集**:
    `restart: unless-stopped` または `restart: always` を有効にします。

    ```yaml
    services:
      app:
        # ...
        # restart: unless-stopped # (デフォルト) 手動停止しない限り再起動
        restart: always           # <--- コメントアウトをこの行に変更または追記
        # ...
    ```

2.  **バックグラウンド実行**:
    `-d` オプションを付けて起動します。
    ```bash
    docker compose up -d --build
    ```

    これで、ラズパイの電源を入れると自動的にコンテナが立ち上がり、エミュレーターが動作を開始します。

### 4. 実行方法 (Windows / Python直接実行)

Windows環境で開発・実行する場合の手順です。

1.  **Python環境の準備**:
    Python 3.10以降がインストールされていることを確認してください。

2.  **依存ライブラリのインストール**:
    ```powershell
    pip install -r requirements.txt
    ```

3.  **設定ファイル (user_settings.yaml) の確認**:
    Windows環境に合わせてCOMポート設定を変更する必要がある場合があります。アプリ起動後、Web UIの[Settings]タブからもBルートID/パスワード等は変更できますが、Wi-SUNデバイスパスは `docker-compose.yml` または 環境変数 (`WI_SUN_DEVICE`) で指定しない場合、デフォルト (`/dev/ttyUSB0` または `COM3` 等) が使用されます。コード内で直接指定するか、環境変数で指定してください。

4.  **アプリケーションの起動**:
    ```powershell
    # プロジェクトルートで実行
    $env:PYTHONPATH="."
    python src/main.py
    ```

### 5. ブラウザでアクセス
起動後、以下のURLにアクセスしてください。
- URL: `http://localhost:8080` (または実行マシンのIPアドレス)

## 使い方

### Dashboardタブ
- **System Status**: 現在のグリッド電力（売買電）、太陽光発電量、蓄電池・V2Hの状態を表示します。
- **Debug Controls**:
    - **Scenario Active**: 自動シミュレーション（シナリオ）のON/OFF。
    - **Manual Sliders**: Load（負荷）、Solar（発電）、Battery/V2H（充放電）、Water Heater（給湯量・加熱）、Air Conditioner（エアコン消費電力）の値を手動で操作し、ECHONET Liteプロパティにリアルタイムで反映させることができます。

### Inspectorタブ
- 内部で保持している各ECHONET Liteオブジェクト（クラスグループ・クラスコード）の状態をツリー形式で確認できます。
- 各プロパティ (EPC) の現在の値をHex形式でリアルタイム表示します。外部からのSETコマンドや内部シミュレーションによる値の変化を確認するのに便利です。

### Settingsタブ
- **Wi-SUN Settings**: Bルート認証ID・パスワードを設定します（変更後は再起動が必要）。
- **Wi-Fi Settings**: Wi-Fi (LAN) 経由でECHONET Lite公開するデバイスを有効/無効で選択できます（太陽光・蓄電池・給湯器・V2H・エアコン）。
- **ECHONET Lite Property Settings**: 各デバイスの識別番号（0x83）・メーカーコード（0x8A）、蓄電池の定格容量、給湯器のタンク容量・加熱電力、V2H の充放電電力、エアコンの消費電力（自動・冷房・暖房・除湿モード共通）などを設定できます。
- 設定は `config/user_settings.yaml` に保存され、次回の起動時に読み込まれます。

## トラブルシューティング
- **ECHONET Lite機器が見つからない**:
    - Docker環境の場合、`network_mode: "host"` になっているか確認してください。
    - Windows/MacのDocker Desktopではホストネットワークモードが完全に機能しないため、Python直接実行を試してください。
    - ファイアウォール設定で UDPポート 3610 および マルチキャスト (224.0.23.0) が許可されているか確認してください。
- **USBドングルが見つからない**:
    - 起動時に警告ログが表示されます。Wi-SUN（Bルート）通信は行われませんが、Wi-Fi接続のECHONET Lite機器として他の機能は動作します。
