# ゲームビジネスニュース自動要約・GitHub Wiki更新システム

RSSフィードからゲームビジネス・業界関連のニュースを自動取得し、LLM（DeepSeek）を用いて要約を生成し、GitHub Wikiリポジトリに自動投稿するシステムです。

## システム概要

- **目的**: RSSからゲームビジネスニュースを取得し、LLMによって要約した上で、GitHub Wikiに毎日自動投稿
- **実行基盤**: GitHub Actions (Ubuntu環境)
- **実行頻度**: 毎日 JST 09:00 の日次バッチ実行
- **使用言語**: Python 3.10以降

## 主要機能

1. **RSS取得**: 設定ファイル(`config/feeds.json`)に基づき複数のゲームニュースRSSフィードから最新記事を取得
2. **時間フィルタリング**: 直近24時間以内に公開された記事のみを抽出
3. **AI要約**: DeepSeek APIを使用して記事を3〜5行の日本語要約に変換
4. **Wiki自動更新**: 生成された要約を日付ベースのMarkdownファイルに整形し、GitHub Wikiリポジトリに自動コミット・プッシュ

## プロジェクト構成

```
.
├── .github/
│   └── workflows/
│       └── update_wiki.yml          # GitHub Actionsワークフロー
├── config/
│   └── feeds.json                   # RSSフィードURL設定
├── docs/
│   ├── deepseek_instructions.md     # 詳細開発指示書
│   └── specification.md             # システム仕様書
├── src/
│   ├── __init__.py
│   ├── main.py                      # メイン統合スクリプト
│   ├── rss_parser.py                # RSS取得・解析モジュール
│   ├── summarizer.py                # DeepSeek API要約モジュール
│   └── wiki_updater.py              # Git操作・Wiki更新モジュール
├── requirements.txt                 # Python依存パッケージ
└── README.md
```

## セットアップ手順

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd gamenews
```

### 2. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの編集
`config/feeds.json` ファイルを編集して取得したいゲームニュースRSSフィードを追加します。

### 4. 環境変数の設定
システムを実行する前に以下の環境変数を設定してください：

```bash
# DeepSeek APIキー（必須）
export LLM_API_KEY="your-deepseek-api-key"

# GitHubトークン（Wiki更新用、オプション）
export GITHUB_TOKEN="your-github-token"
```

### 5. システムのテスト実行
```bash
# テストモードで実行
python src/main.py --test-mode

# 通常モードで実行
python src/main.py
```

## GitHub Actionsによる自動実行設定

### 必要なGitHub Secrets
1. **LLM_API_KEY**: DeepSeek APIキー
2. **GITHUB_TOKEN**: GitHubトークン（自動生成され、Wiki更新に使用）
3. **WIKI_REPO_URL** (オプション): 更新対象のWikiリポジトリURL（例: `https://github.com/username/repo.wiki.git`）

### ワークフロー設定
- **スケジュール実行**: 毎日UTC 00:00（日本時間09:00）に自動実行
- **手動実行**: GitHub ActionsのUIから任意のタイミングで実行可能
- **テストモード**: 手動実行時にAPI呼び出しをスキップしてテスト可能

## 開発指針

### 言語設定
- **コードコメント・docstring**: すべて日本語
- **変数・関数名**: 明確な英語（ローマ字命名禁止）
- **出力テキスト**: 日本語

### セキュリティ
- APIキーやトークンはコード内にハードコードせず、環境変数から読み込む
- GitHub Secretsを活用して機密情報を管理

### エラーハンドリング
- 一部のフィードや記事でエラーが発生してもシステム全体が停止しない
- 適切なログ出力とエラー回復機構を実装

## 使用ライブラリ

- `feedparser`: RSS/Atomフィードのパース
- `requests`: HTTP通信
- `beautifulsoup4`: HTMLパース・クレンジング
- `openai`: DeepSeek APIクライアント（OpenAI互換）
- `pytz`: タイムゾーン処理

## ライセンス

このプロジェクトはオープンソースとして公開されています。詳細はLICENSEファイルを参照してください。

## 詳細仕様

詳細な仕様や開発指示については `docs/` ディレクトリ内のドキュメントを参照してください。

- `docs/deepseek_instructions.md`: 実装担当AI向け詳細開発指示
- `docs/specification.md`: システム仕様書