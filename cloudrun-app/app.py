import os

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

app = Flask(__name__)

# 環境変数設定
database = os.environ.get('POSTGRES_DATABASE', 'guestbook')
user = os.environ.get('POSTGRES_USER', 'postgres')
password = os.environ.get('POSTGRES_PASSWORD', '')
host = os.environ.get('POSTGRES_HOST', 'localhost')
port = os.environ.get('POSTGRES_PORT', '5432')

# PostgreSQL データベース接続設定
app.config['SQLALCHEMY_DATABASE_URI'] =  f"postgresql://{user}:{password}@{host}:{port}/{database}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy の初期化
class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# テーブルモデルの定義
class Entry(db.Model):
    __tablename__ = 'entries'
    entryid = db.Column(db.Integer, primary_key=True)
    guestname = db.Column(db.String(255), nullable=False)
    content = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        """エントリを辞書形式に変換"""
        return {
            'entryID': self.entryid,
            'guestName': self.guestname,
            'content': self.content,
        }

@app.route('/entries', methods=['GET'])
def get_entries():
    """全エントリを取得するエンドポイント"""
    try:
        # 全エントリを取得
        entries = Entry.query.all()

        # 結果を JSON 形式で返す
        return jsonify([entry.to_dict() for entry in entries]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# # データベースの初期化 (初回のみ必要)
# @app.before_first_request
# def initialize_database():
#     """データベースとテーブルを作成"""
#     db.create_all()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080,debug=False)
