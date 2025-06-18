# FastAPIスターターキット

このリポジトリはFastAPI開発用の基本セットアップを提供するスターターキットです。必要なツールや設定が含まれています。

## 特徴
- FastAPIのアプリケーション構造がセットアップ済み。
- コンテナ開発用のDockerおよびdocker-composeの設定。
- 依存管理用に設定済みの [pyproject.toml](pyproject.toml:1)。
- サンプルのAPIエントリーポイントは [`api/main.py`](api/main.py:1) にあります。

## 必要条件
- Python 3.8以上
- コンテナ開発を利用する場合、Dockerが必要です。

## 始め方

### ローカル環境でのセットアップと実行
1. 依存関係をインストール:
   ```
   pip install -r requirements.txt  # もしくは、pyproject.tomlに記載されたpoetry/pipenvを使用してください
   ```
2. FastAPIサーバを起動:
   ```
   uvicorn api.main:app --reload
   ```

### Dockerの利用
1. コンテナのビルド:
   ```
   docker-compose build
   ```
2. コンテナの起動:
   ```
   docker-compose up
   ```

## プロジェクト構成

```
.
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── api
    ├── __init__.py
    └── main.py
```

## コントリビューション

改善のための提案やプルリクエストは歓迎します。問題やアイデアがあればIssueを作成してください。