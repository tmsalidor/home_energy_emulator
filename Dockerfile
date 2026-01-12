FROM python:3.10-slim

WORKDIR /app

# 依存ライブラリのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY . .

# ECHONET Lite (UDP 3610) と GUI (ポート指定が必要、デフォルト8080等) を公開
EXPOSE 3610/udp 8080

CMD ["python", "src/main.py"]
