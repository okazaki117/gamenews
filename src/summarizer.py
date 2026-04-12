import os
import time
from typing import Dict, Any, Optional
from openai import OpenAI
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """DeepSeek APIを使用して記事の要約を生成するクラス"""

    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        """
        要約クラスの初期化

        Args:
            max_retries (int): API呼び出し失敗時の最大リトライ回数
            retry_delay (int): リトライ間の遅延時間（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = self._initialize_client()

    def _initialize_client(self) -> Optional[OpenAI]:
        """OpenAI互換クライアントをDeepSeek用に初期化"""
        api_key = os.environ.get("LLM_API_KEY")

        if not api_key:
            logger.error("環境変数 'LLM_API_KEY' が設定されていません")
            logger.info("GitHub Actionsでは、シークレットとして 'LLM_API_KEY' を設定してください")
            return None

        try:
            # DeepSeek APIはOpenAI互換エンドポイントを提供
            # base_urlをDeepSeekのアドレスに設定
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            logger.info("DeepSeek APIクライアントを初期化しました")
            return client
        except Exception as e:
            logger.error(f"APIクライアントの初期化に失敗しました: {e}")
            return None

    def _truncate_text(self, text: str, max_tokens: int = 12000) -> str:
        """
        テキストをトークン数制限に合わせて切り詰める（簡易実装）

        Args:
            text (str): 入力テキスト
            max_tokens (int): 最大トークン数（概算）

        Returns:
            str: 切り詰められたテキスト
        """
        # 簡易的な実装：文字数で概算（1トークン ≈ 4文字）
        max_chars = max_tokens * 4

        if len(text) <= max_chars:
            return text

        logger.warning(f"テキストが長すぎるため切り詰めます: {len(text)}文字 → {max_chars}文字")
        return text[:max_chars] + "..."

    def _call_api_with_retry(self, messages: list, retry_count: int = 0) -> Optional[str]:
        """
        リトライ機構付きでDeepSeek APIを呼び出す

        Args:
            messages (list): チャットメッセージのリスト
            retry_count (int): 現在のリトライ回数

        Returns:
            Optional[str]: 要約テキスト（失敗時はNone）
        """
        if not self.client:
            logger.error("APIクライアントが初期化されていません")
            return None

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.3,  # 低めの温度で一貫性のある出力
                max_tokens=500,   # 要約の最大トークン数
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"API呼び出し成功: {len(summary)}文字の要約を生成")
            return summary

        except Exception as e:
            error_msg = str(e)

            # レート制限エラーの検出
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                logger.warning(f"レート制限エラー: {error_msg}")
            elif "timeout" in error_msg.lower():
                logger.warning(f"タイムアウトエラー: {error_msg}")
            else:
                logger.error(f"API呼び出しエラー: {error_msg}")

            # リトライ判定
            if retry_count < self.max_retries:
                logger.info(f"{self.retry_delay}秒後にリトライします... ({retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self._call_api_with_retry(messages, retry_count + 1)
            else:
                logger.error(f"最大リトライ回数({self.max_retries})に達しました。要約をスキップします")
                return None

    def summarize_article(self, article: Dict[str, Any]) -> Optional[str]:
        """
        記事の本文を要約する

        Args:
            article (Dict[str, Any]): 記事情報
                - title: 記事タイトル
                - plain_text: 記事本文（プレーンテキスト）
                - url: 記事URL
                - feed_name: フィード名

        Returns:
            Optional[str]: 要約テキスト（失敗時はNone）
        """
        if not self.client:
            logger.error("APIクライアントが利用できないため要約をスキップします")
            return None

        title = article.get('title', 'タイトルなし')
        plain_text = article.get('plain_text', '')
        url = article.get('url', '')
        feed_name = article.get('feed_name', '不明なフィード')

        if not plain_text:
            logger.warning(f"記事 '{title}' には本文が含まれていません")
            return None

        logger.info(f"記事を要約中: {title}")

        # テキストが長すぎる場合は切り詰める
        truncated_text = self._truncate_text(plain_text)

        # システムプロンプト（日本語）
        system_prompt = """あなたはゲームビジネスニュースの専門アシスタントです。
与えられた記事の重要なポイントを、以下の要件で日本語で要約してください：

1. 3〜5行程度の箇条書き形式でまとめる
2. ビジネスや業界への影響に焦点を当てる
3. 簡潔で分かりやすい日本語を使用する
4. 主観的な意見は避け、事実に基づいた要点を抽出する"""

        # ユーザープロンプト（記事情報を含む）
        user_prompt = f"""以下のゲームニュース記事を要約してください：

【記事タイトル】{title}
【出典】{feed_name}
【URL】{url}

【記事本文】
{truncated_text}

上記の記事の重要なポイントを、ゲームビジネスや業界への影響に焦点を当てて、3〜5行程度の箇条書きで要約してください。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # API呼び出し（リトライ付き）
        summary = self._call_api_with_retry(messages)

        if summary:
            # 要約にメタ情報を追加
            enhanced_summary = f"""## {title}

**出典**: {feed_name} | [元記事]({url})

### 要点
{summary}

---
"""
            return enhanced_summary
        else:
            logger.error(f"記事 '{title}' の要約生成に失敗しました")
            return None

    def summarize_multiple_articles(self, articles: list) -> list:
        """
        複数の記事を要約する

        Args:
            articles (list): 記事情報のリスト

        Returns:
            list: 要約結果のリスト（失敗した記事はスキップ）
        """
        logger.info(f"{len(articles)}件の記事を要約します")

        summaries = []
        successful = 0
        failed = 0

        for i, article in enumerate(articles, 1):
            logger.info(f"記事 {i}/{len(articles)} を処理中...")

            summary = self.summarize_article(article)

            if summary:
                summaries.append(summary)
                successful += 1
                logger.info(f"記事 {i} の要約に成功")
            else:
                failed += 1
                logger.warning(f"記事 {i} の要約をスキップ")

            # API負荷軽減のため少し待機
            time.sleep(1)

        logger.info(f"要約完了: {successful}件成功, {failed}件失敗")
        return summaries


def main():
    """テスト用のメイン関数"""
    # テスト用の記事データ
    test_article = {
        'title': 'ゲーム業界の最新動向',
        'plain_text': 'ゲーム業界では、モバイルゲーム市場が拡大を続けており、特にアジア地域での成長が著しい。新興企業によるイノベーションと、既存大手企業の戦略転換が同時進行している。また、クラウドゲーミングやメタバース関連技術への投資も活発化している。',
        'url': 'https://example.com/article1',
        'feed_name': 'テストフィード'
    }

    summarizer = ArticleSummarizer()

    # 環境変数が設定されているか確認
    if not os.environ.get("LLM_API_KEY"):
        logger.warning("テスト実行: LLM_API_KEY環境変数が設定されていないため、ダミー要約を生成します")
        # ダミー要約を生成
        dummy_summary = """## ゲーム業界の最新動向

**出典**: テストフィード | [元記事](https://example.com/article1)

### 要点
- モバイルゲーム市場が継続的に拡大、特にアジア地域で成長が顕著
- 新興企業のイノベーションと既存大手企業の戦略転換が同時進行
- クラウドゲーミングやメタバース関連技術への投資が活発化

---
"""
        print("生成された要約:")
        print(dummy_summary)
    else:
        summary = summarizer.summarize_article(test_article)
        if summary:
            print("生成された要約:")
            print(summary)
        else:
            print("要約生成に失敗しました")


if __name__ == "__main__":
    main()