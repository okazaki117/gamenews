import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import feedparser
from bs4 import BeautifulSoup
import pytz


class RSSParser:
    """RSSフィードから記事を取得し、直近24時間以内の記事を抽出するクラス"""

    def __init__(self, config_path: str = "config/feeds.json"):
        """
        RSSパーサーの初期化

        Args:
            config_path (str): RSSフィード設定ファイルのパス
        """
        self.config_path = config_path
        self.feeds = self._load_feeds()
        self.jst = pytz.timezone('Asia/Tokyo')

    def _load_feeds(self) -> List[Dict[str, Any]]:
        """設定ファイルからRSSフィード情報を読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                feeds = json.load(f)
            print(f"設定ファイルから {len(feeds)} 個のフィードを読み込みました")
            return feeds
        except FileNotFoundError:
            print(f"エラー: 設定ファイル '{self.config_path}' が見つかりません")
            return []
        except json.JSONDecodeError as e:
            print(f"エラー: 設定ファイルのJSON解析に失敗しました: {e}")
            return []

    def _extract_plain_text(self, html_content: str) -> str:
        """
        HTMLコンテンツからプレーンテキストを抽出する

        Args:
            html_content (str): HTML形式のコンテンツ

        Returns:
            str: プレーンテキスト
        """
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # スクリプトやスタイルタグを除去
            for script in soup(["script", "style"]):
                script.decompose()

            # テキストを抽出し、余分な空白を整理
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            print(f"HTMLテキスト抽出エラー: {e}")
            return html_content

    def _is_within_24_hours(self, published_time: datetime) -> bool:
        """
        記事の公開日時が直近24時間以内か判定する

        Args:
            published_time (datetime): 記事の公開日時

        Returns:
            bool: 直近24時間以内ならTrue
        """
        now_jst = datetime.now(self.jst)
        time_diff = now_jst - published_time
        # 最新記事のみを収集（週末の更新ストップを考慮して直近48時間以内の記事を対象とする）
        return time_diff <= timedelta(hours=48)

    def _parse_article_date(self, entry) -> datetime:
        """
        フィードエントリから公開日時をパースする

        Args:
            entry: feedparserエントリ

        Returns:
            datetime: パースされた日時（JST）
        """
        # 優先順位: published_parsed > updated_parsed > 現在時刻
        time_tuple = None

        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            time_tuple = entry.published_parsed
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            time_tuple = entry.updated_parsed

        if time_tuple:
            # time_tupleはUTCのstruct_time
            utc_time = datetime(*time_tuple[:6], tzinfo=pytz.UTC)
            jst_time = utc_time.astimezone(self.jst)
            return jst_time
        else:
            # 日時情報がない場合は現在時刻を使用（フィルタリングの対象外になる）
            return datetime.now(self.jst)

    def fetch_recent_articles(self) -> List[Dict[str, Any]]:
        """
        各RSSフィードから直近24時間以内の記事を取得する

        Returns:
            List[Dict[str, Any]]: 記事情報のリスト
        """
        all_articles = []

        for feed in self.feeds:
            feed_name = feed.get('name', 'Unknown')
            feed_url = feed.get('url', '')

            if not feed_url:
                print(f"警告: フィード '{feed_name}' にURLが設定されていません")
                continue

            print(f"フィード '{feed_name}' から記事を取得中...")

            try:
                # RSSフィードの取得とパース
                parsed_feed = feedparser.parse(feed_url)

                if parsed_feed.bozo:
                    print(f"警告: フィード '{feed_name}' のパースに問題があります: {parsed_feed.bozo_exception}")
                    # continueせずにエラーだけ出して進める（パース自体は成功している場合が多いため）

                entries = parsed_feed.entries
                if not entries:
                    continue
                print(f"フィード '{feed_name}' から {len(entries)} 件の記事を取得しました")

                for entry in entries:
                    try:
                        # 記事の公開日時を取得
                        published_time = self._parse_article_date(entry)

                        # 直近24時間以内の記事のみ処理
                        if not self._is_within_24_hours(published_time):
                            continue

                        # 記事情報を抽出
                        title = entry.get('title', 'タイトルなし')
                        article_url = entry.get('link', '')
                        description = entry.get('description', '')
                        content = entry.get('content', [{}])[0].get('value', '') if hasattr(entry, 'content') else ''

                        # 本文を優先的に使用（description or content）
                        html_content = content if content else description

                        # HTMLからプレーンテキストを抽出
                        plain_text = self._extract_plain_text(html_content)

                        article_info = {
                            'title': title,
                            'url': article_url,
                            'plain_text': plain_text,
                            'feed_name': feed_name,
                            'published_time': published_time.isoformat(),
                            'source_url': feed_url
                        }

                        all_articles.append(article_info)
                        print(f"  記事を追加: {title[:50]}...")

                    except Exception as e:
                        print(f"記事処理エラー（フィード: {feed_name}）: {e}")
                        continue

            except Exception as e:
                print(f"フィード取得エラー（{feed_name}）: {e}")
                continue

        print(f"合計 {len(all_articles)} 件の直近24時間以内の記事を取得しました")
        return all_articles


def main():
    """テスト用のメイン関数"""
    parser = RSSParser()
    articles = parser.fetch_recent_articles()

    if articles:
        print("\n取得した記事一覧:")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   公開日時: {article['published_time']}")
            print(f"   フィード: {article['feed_name']}")
            print(f"   本文の長さ: {len(article['plain_text'])} 文字")
            print()
    else:
        print("直近24時間以内の記事は見つかりませんでした")


if __name__ == "__main__":
    main()