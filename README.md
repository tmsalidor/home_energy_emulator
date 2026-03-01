# Home Energy Emulator with ECHONET Lite

<img width="1253" height="1516" alt="image" src="https://github.com/user-attachments/assets/fe78bbae-866a-495b-b314-df96fc29452c" />


ECHONET Liteプロパティに対応したHEMS (Home Energy Management System) 対応機器エミュレーターです。
スマートメーター (Bルート対応)、太陽光発電システム、蓄電池システム、電気自動車充放電器 (V2H)、電気給湯器、家庭用エアコンをエミュレートし、NiceGUIによるWebインターフェースで状態監視・操作が可能です。

## 特徴
- **ハイブリッド通信エミュレーション**:
    - **スマートメーター**: Wi-SUN (Bルート) 経由でのプロパティ公開。実際のUSBドングル (BP35A1等) または仮想COMポートを通じてシリアル通信を行います。未接続時には無効化。
    - **その他デバイス**: Wi-Fi (LAN) 経由でのECHONET Liteプロパティ公開 (UDP/Multicast)。
- **Web UI**:
    - **Dashboard**: 各デバイスの発電・充放電状態や消費電力のリアルタイム監視と、スライダーによる手動シミュレーション操作。
    - **Scenarios**: 機器の動作シナリオ（CSV形式）のアップロード、作成、編集、実行管理。1時間ごとの発電量・消費電力の変化を自動シミュレート可能。
    - **Settings**: Web画面上でのデバイス有効/無効の切り替えやパラメータ設定（Wi-SUN設定等）。入力値は即座にエンジンへ反映（一部項目を除く）。
    - **Inspector**: ECHONET Liteプロパティの内部値をリアルタイムで確認できるデバッグ機能。
    - **Version Information**: Gitのコミットハッシュと日時を画面下部に表示し、実行中のバージョンを即座に確認可能。
- **ECHONET Liteプロパティ対応**:
    - **スマートメーター**: 瞬時電力 (0xE7)、積算電力量 (0xE0, 0xE3) など。
    - **太陽光発電**: 瞬時発電電力 (0xE0)、積算発電量 (0xE1) など。
    - **蓄電池**: SOC残量 (0xE4), 蓄電残容量Wh (0xE2), 定格容量 (0xD0), 運転モード (0xDA), 充放電電力 (0xD3), 充電/放電上限・可能容量 (0xA0〜0xA5), 積算充放電量 (0xA8, 0xA9) など。
    - **電気自動車充放電器 (V2H)**: 車両接続確認 (0xCD), 運転モード (0xDA), 瞬時充放電電力 (0xD3), SOC残量 (0xE4), 放電可能容量/残容量 (0xC0, 0xC2, 0xE2), 積算充放電量 (0xD6, 0xD8), 充放電電力設定値 (0xEB, 0xEC) など。
    - **電気給湯器**: 運転状態 (0x80)、沸き上げ自動設定 (0xB0)、沸き上げ中状態 (0xB2)、残湯量 (0xE1)、タンク容量 (0xE2)、風呂自動モード設定 (0xE3)、昼間沸き増し停止設定 (0xC0)。
    - **家庭用エアコン**: 運転状態 (0x80)、運転モード設定 (0xB0)、温度設定値 (0xB3)、風量設定 (0xA0)、節電動作設定 (0x8F)、瞬時消費電力計測値 (0x84)、積算消費電力量計測値 (0x85)。

## 必要要件
- **ハードウェア環境**:
    - Wi-SUN USBドングル (ローム社製 BP35A1 等) - Bルート通信エミュレーション用 
    - Raspberry Pi (3B+, 4B, 5 等) 推奨 - 常時稼働用サーバーとして適しています。
- **ソフトウェア環境**:
    - **推奨**: Linux (Ubuntu, Raspberry Pi OS) - Docker (`network_mode: host`) がネイティブ動作するため、ECHONET Liteのマルチキャスト通信に最適です。
    - **Windows**: Python直接実行を推奨 (Docker Desktop for Windowsはネットワーク制限によりマルチキャストが正しく機能しない場合があります)。

## セットアップと実行

### 1. 構成ファイル (オプション)
`config/user_settings.yaml` でデバイスIDやパラメータを事前定義できますが、初回起動後にWeb UIの**Settings**タブからも設定可能です。

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
    Windows環境に合わせてCOMポート設定を変更する必要がある場合があります。アプリ起動後、Web UIの**Settings**タブからもBルート設定等は変更できますが、Wi-SUNデバイスパスは `docker-compose.yml` または 環境変数 (`WI_SUN_DEVICE`) で指定しない場合、デフォルト (`/dev/ttyUSB0` または `COM3` 等) が使用されます。コード内で直接指定するか、環境変数で指定してください。

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

### Dashboard タブ
- **System Status**: 現在のグリッド電力（売買電）、太陽光発電量、蓄電池・V2H・給湯器・エアコンの状態をカード形式で表示します。
- **Control Sliders**:
    - **Manual Sliders**: Load（負荷）、Solar（発電）、Battery/V2H（充放電）、Water Heater（給湯量・加熱）、Air Conditioner（エアコン消費電力）の値を手動で操作し、ECHONET Liteプロパティにリアルタイムで反映させることができます。
    - **Scenario Mode**: Scenariosタブで設定したCSVシナリオを実行している間は、スライダーによる手動設定はシナリオ値によって上書きされます。手動操作を行いたい場合は Scenario Active状態を解除してください。

### Scenarios タブ (New)
- **シナリオの管理**: 定義済みのCSVシナリオファイルを選択、複製、アップロード、名前変更、削除できます。デフォルトシナリオ(`default_scenario.csv`)も同梱されています。
- **データエディタ**: 直感的なテーブルインタフェースで、時間(Time)ごとの負荷電力(Load W)と太陽光発電量(Solar W)を1時間単位で直接編集できます。行の追加や削除、保存が画面上で完結します。
- **グラフプレビュー**: 選択したシナリオの電力推移（負荷と発電予測）をスムーズなチャートでプレビュー確認できます。

### Settings タブ
- **Wi-SUN Settings**: Bルート認証ID・パスワードを設定します。
- **Network Devices**: Wi-Fi経由で公開するECHONET Liteデバイス（太陽光・蓄電池・給湯器・V2H・エアコン）を個別に有効/無効化できます。
- **Device Parameters**: 各デバイスのノードプロファイル（識別番号・メーカーコード）、定格容量、タンク容量、最大充放電電力などを設定します。
- **設定の即時反映**: デバイスのON/OFFや定格容量などのパラメータ変更は即時にエンジンへ反映されます。（※Wi-SUNの認証関連など一部の根幹機能は再起動が必要な場合があります）。設定は `config/user_settings.yaml` に自動保存されます。

### Inspector タブ
- 内部で保持している各ECHONET Liteオブジェクト（クラスグループ・クラスコード）の状態をツリー形式で確認できます。
- 各プロパティ (EPC) の現在の値をHex形式でリアルタイム表示します。HEMSコントローラーからのSET要求や内部シミュレーションによる値の変化のトラッキングに役立ちます。

## ⚠️ 注意事項

### データの揮発性（再起動によるリセット）

このエミュレーターはすべての状態をメモリ上で管理しているため、**アプリケーションを停止・再起動するたびに以下のシミュレーション実測値はリセット**されます。

| リセットされる値 | 対象デバイス | 備考 |
|---|---|---|
| SOC (State of Charge)、残湯量 | 蓄電池、V2H、給湯器 | 起動時に50%に初期化されます |
| 積算電力量 (充電・放電・発電など) | 蓄電池、V2H、太陽光発電、スマートメーター、エアコン | 0 にリセットされます |

**※Settingsタブで入力したデバイス設定パラメータや、Scenariosタブで作成・保存したCSVファイルは永続化されます。**

### ECHONETマルチキャストとWindowsの制限

Windows環境（特にDocker Desktop for Windows）では、ECHONET LiteのUDPマルチキャスト（224.0.23.0:3610）の送受信がホストネットワークの制限により正しく機能しない場合があります。HEMSコントローラー等から機器が検索できない場合は、**Windows上でPythonを直接実行**してください。

## トラブルシューティング
- **ECHONET Lite機器が見つからない**:
    - Docker環境の場合、`docker-compose.yml` で `network_mode: "host"` になっているか確認してください。
    - Windows/OS X のDocker環境ではホストモードが制限されるため、Pythonを直接実行してください。
    - ファイアウォール設定で UDPポート 3610 および マルチキャスト (224.0.23.0) が許可されているか確認してください。
- **USBドングルへのアクセスエラー**:
    - 起動時にCOMポートや `/dev/ttyUSB0` の警告が出る場合、権限（chmod）やポート番号の指定（WindowsならCOM3等）を見直してください。Wi-SUN通信は行われませんが、Wi-Fi接続のECHONET Lite機器としての機能は影響を受けません。