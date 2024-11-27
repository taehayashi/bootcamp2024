# ベースイメージとして Python 3.11 を使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# アプリケーションの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY app.py .

# Flask アプリケーションを実行するポートを公開
EXPOSE 8080

# コンテナ起動時のデフォルトコマンド
CMD ["python", "app.py"]