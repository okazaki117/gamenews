# AI実装者（DeepSeek等）向け 必読の実装ガイドラインとアンチパターン

本ドキュメントは、過去のプロジェクトで実際に行われたAIによる実装での「想定外の不具合」や「仕様の勘違い」から得られた教訓をまとめたものです。
AIが実装を担当する際は、以下のアンチパターンに陥っていないかを必ずセルフチェックしてください。

## 1. クロスプラットフォーム互換性の軽視（特にWindows固有コマンドの罠）

### ❌ アンチパターン
Pythonスクリプト上で外部コマンドを叩く際、開発環境（Windows等）に依存したコマンドを `subprocess` で呼び出してしまう。
- 例: 古いディレクトリを削除するために `subprocess.run('rmdir /s /q "wiki"', shell=True)` を実行する。
- **結果**: 実行環境であるGitHub Actions（Ubuntu/Linux）上で `rmdir` コマンドがエラー（不正な引数と解釈される）となり、後続のプログラムが失敗する。

### ✅ ベストプラクティス
OSに依存しない**Pythonの標準ライブラリ**を常に最優先で使用すること。
- 例: `import shutil; shutil.rmtree("wiki", ignore_errors=True)` を使用する。

---

## 2. GitHub ActionsやGit認証URLの仕様忘れ

### ❌ アンチパターン
GitHub Actionsなどの環境で、`GITHUB_TOKEN` を使ってリポジトリを `git clone` / `push` するための認証URLを構築する際、トークン単体を含めてしまう。
- 例: `https://${GITHUB_TOKEN}@github.com/username/repo.git`
- **結果**: Gitクライアントはトークンを「パスワード」ではなく「ユーザー名」として認識しようとする場合や、認証プロンプトが表示され自動システムが `could not read Password` パニックを起こして停止する。

### ✅ ベストプラクティス
必ず「ユーザー名」として `x-access-token`（またはそれに準ずるもの）を指定したURLフォーマットにする。
- 例: `https://x-access-token:${GITHUB_TOKEN}@github.com/username/repo.git`

---

## 3. GitHub Actions と Python ロギング（バッファ・途中終了）の罠

### ❌ アンチパターン
障害発生時のために `try-except` で `logger.error()` や `sys.exit(1)` を設定して安心してしまう。
- **結果**: GitHub Actions はシェルスクリプトの途中で `exit 1` などが返るとその時点で強制終了し、しかもPythonの標準出力がバッファリングされていると「終了直前の重要なエラーログ（なぜ終了したか）」が画面に表示されないままプロセスが死んでしまう。デバッグが極めて困難になる。

### ✅ ベストプラクティス
1. **バッファの無効化**: GitHub ActionsでPythonを呼ぶ際は環境変数 `PYTHONUNBUFFERED=1` を必ず指定し、リアルタイムでログをフラッシュさせること。
2. **ロガーの強制上書き**: 複数のモジュールで `logging.basicConfig()` が不用意に呼ばれることを防ぐため、メインスクリプトで `force=True` を指定して標準出力に明示的に吐き出す設定を行うこと。
3. **シェルの中断回避**: 必要に応じて、Actionsの yaml 側で `set +e` と `set -e` でエラー発生ステップを挟み、`EXIT_CODE=$?` 等で終了コードを明示的にキャッチして後から `exit` するように構築すること。
