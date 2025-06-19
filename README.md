# Komei Shimbun AI Transcriptor

## 概要
「Komei Shimbun AI Transcriptor」は、FastAPIを用いた音声テキスト起こしAPIサーバです。アップロードされた音声ファイルに対し、OpenAI Whisper APIを利用して効率的かつ高精度な文字起こしを実施します。パッケージ管理はPoetry、コンテナ管理はDocker Composeで行われ、環境変数は.envファイルに設定されています。

## 主な機能
- **音声ファイルのアップロードと前処理**  
  ユーザーからの音声ファイルを受け取り、ファイルサイズや形式の検証、必要に応じたMP3形式への変換、10分以上の音声の場合の分割を実施します。

- **文字起こし処理**  
  OpenAI Whisper API（whisper-1モデル）を使用し、非同期処理により複数のファイルの文字起こしを並列で実行。各ファイルの結果は統合され、タイムスタンプ付きのセグメントテキストとして提供されます。

- **結果の保存とダウンロード**  
  文字起こし結果はユーザーごとに整理され、「transcription_results」ディレクトリに保存されます。専用のエンドポイントからファイルのダウンロードが可能です。

- **UI提供**  
  静的HTML（index.html）を返す「/ui」エンドポイントにより、利用者に対して簡易的なユーザーインターフェースを提供します。アクセス時にはファイルの自動クリーンアップも実施されます。

## 技術／アーキテクチャ
- **バックエンド**: FastAPIを利用した高速・効率的なAPIサーバ実装
- **非同期処理**: async/await構文を用いて、複数ファイルの文字起こし処理を並列に実行
- **データバリデーション**: Pydanticを活用し、リクエストおよびレスポンスのデータ検証を実施
- **音声処理**: pydubライブラリによって、音声ファイルの読み込み、変換、分割、長さの計測を行う
- **外部連携**: OpenAI Whisper API（whisper-1モデル）を使用し、高精度な文字起こしを実現
- **ファイル管理**: アップロードされたファイルはユーザーごとに整理され、処理済みファイルは「processed_audio」、文字起こし結果は「transcription_results」に格納
- **環境設定**: .envファイルに環境変数を設定し、Docker Composeでコンテナ管理、Poetryで依存関係管理を実施

## API エンドポイント
- **POST /okoshi**  
  音声ファイルのアップロード・検証、保存、必要に応じた形式変換および分割、そしてOpenAI Whisperによる文字起こし処理を実行します。

- **GET /download/transcription/{filename}**  
  文字起こし結果ファイルのダウンロードを提供します。ディレクトリトラバーサル防止対策が実装されています。

- **GET /ui**  
  静的HTML（index.html）を返すことで、利用者用の簡易UIを提供します。エンドポイントへのアクセス時には、ファイルクリーンアップ処理も実行されます。

## ディレクトリ構成
- **api/**: FastAPIの主要ソースコード（エンドポイント、ルーティング、ユーティリティ）
  - **routers/**: 各エンドポイント（/okoshi、/uiなど）の実装
  - **schemas/**: Pydanticを用いたリクエスト/レスポンスのデータ検証モデル
  - **utils/**: 音声処理やWhisper API連携のためのユーティリティ
- **processed_audio/**: 処理済みの音声ファイルを格納するディレクトリ
- **transcription_results/**: 文字起こし結果ファイルの保存先
- **その他**: Docker関連ファイル（Dockerfile、docker-compose.yml、.dockerignore）およびPoetry管理ファイル（pyproject.toml、poetry.lock）

## セットアップと実行方法
1. **依存関係のインストール**  
   Poetryを使用して、以下のコマンドで依存関係をインストールします:
   ```
   poetry install
   ```

2. **環境変数の設定**  
   プロジェクトルートに.envファイルを作成し、必要な環境変数（例: OPENAI_API_KEY）を設定してください。

3. **サーバの起動**  
   Docker Composeを使用する場合:
   ```
   docker-compose up --build
   ```
   または直接FastAPIサーバを起動する場合:
   ```
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

