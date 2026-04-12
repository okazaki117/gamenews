# DeepSeek 修正パッチ指示書 (Feature: 全体トレンド要約とタイトル日本語化)

このドキュメントは、システム全体のアーキテクト（Antigravity）から実装担当AI（DeepSeek等）へ向けた具体的な機能追加要件の指示書です。
**必ず `docs/deepseek_instructions.md` および `docs/AI_IMPLEMENTATION_GUIDELINES.md` のアンチパターンガイドラインを事前に熟読した上で実装を開始してください。**

## 1. 今回の機能追加の目的
ユーザーが短時間でゲーム業界のニュースをより直感的に把握できるよう、以下の2つの機能を追加します。
1. **各記事の表題（タイトル）の日本語化**: 海外RSS特有の英語タイトルを要約時に日本語に翻訳し、Markdownの各種見出しとして自然に表示させる。
2. **全体トレンド要約（サマリー）の冒頭配置**: その日取得した全記事の要約を元に、「今日のトレンド一覧」を生成し、Wiki記事の一番上に表示する。

---

## 2. 実装指示（修正を加えるコンポーネントごとの詳細）

### 2-1. `src/summarizer.py` の修正
1. **個別要約プロンプトの改修 (`summarize_article`周辺)**:
   - システムプロンプトを変更し、以下のような指示を含めてください：
     「あなたはプロのゲーム記事の翻訳・要約編集者です。記事の元の表題（タイトル）を自然な日本語に翻訳し出力の先頭につけ、その後に本編の要点を3行の箇条書きでまとめて出力してください。」
   - もし、現状で rss_parser から受け取った `article['title']` をそのままMarkdownの見出しに使っている場合、AIから返却された出力結果の中から「翻訳されたタイトル」を取り出せるように出力フォーマット（JSONや特定接頭辞）を工夫するか、あるいはWiki生成側でAIの出力をそのまま一つのブロックとして扱うように設計を変更してください。
2. **全体トレンド要約メソッド (`summarize_daily_trends`) の新規追加**:
   - `def summarize_daily_trends(self, summaries: List[str]) -> str:` のようなメソッドを新設してください。
   - `summaries` を結合した長文を投げ、「これら今日のゲームニュースの全ての内容から、注目のトレンドや重要な動きを3行〜4行程度で端的に要約してください。」というプロンプトを実行し、結果を返却してください。

### 2-2. `src/wiki_updater.py` の修正
- `generate_markdown_content(self, summaries: List[str], ...)` 等の生成関数に、新たな引数 `daily_trend_summary: str` を追加等してください。
- 出力されるMarkdownの冒頭（例：「## 概要」の下）に、「## 今日のゲーム業界トレンド」等の見出しで全体要約テキストを挿入するようにフォーマットを変更してください。

### 2-3. `src/main.py` の修正
- `run_pipeline` メソッド等のフローを以下のように変更してください：
  1. `self.fetch_articles()`
  2. `self.summarizer.summarize_articles(articles)`
  3. **[NEW]** `self.summarizer.summarize_daily_trends(summaries)` (※個別要約の結果から全体要約を生成)
  4. `self.wiki_updater.update_wiki(summaries, daily_trend_summary, wiki_repo_url)` (※必要に応じた引数の連携)

---

## 3. 実装上の厳守事項（再確認）
- **プロンプトテスト**: 追加する全体要約は、トークン数が重くなる可能性があります。適切なテキストの短縮（Truncate）が行われるよう既存関数を再利用してください。
- **実行の安全性**: これまでの実装パッチで直した、「Windows固有コマンドの排除(`shutil.rmtree`)の使用」や「Gitクローンの `x-access-token:` 付与」、「PYTHONUNBUFFERED等のバッファ対策」などの設定を、リファクタリングによって**絶対に元に戻さない・破壊しない**でください。既存の安定稼働しているコアシェルロジックには触れず、今回は「AI要約関数周り」と「Markdownのフォーマット」のみを変更してください。
