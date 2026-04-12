import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any

# ローカルモジュールのインポート
from src.rss_parser import RSSParser
from src.summarizer import ArticleSummarizer
from src.wiki_updater import WikiUpdater

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger(__name__)


class GameNewsPipeline:
    """ゲームニュース取得・要約・Wiki更新の統合パイプライン"""

    def __init__(self, config_path: str = "config/feeds.json", wiki_repo_path: str = "wiki"):
        """
        パイプラインの初期化

        Args:
            config_path (str): RSSフィード設定ファイルのパス
            wiki_repo_path (str): Wikiリポジトリのローカルパス
        """
        self.config_path = config_path
        self.wiki_repo_path = wiki_repo_path
        self.rss_parser = None
        self.summarizer = None
        self.wiki_updater = None
        
        # 環境変数の確認
        self._check_environment()

    def _check_environment(self):
        """必要な環境変数が設定されているか確認"""
        # LLM APIキーの確認
        llm_api_key = os.environ.get("LLM_API_KEY")
        if not llm_api_key:
            logger.warning("環境変数 'LLM_API_KEY' が設定されていません。")
            logger.warning("テストモードで実行するか、環境変数を設定してください。")
        
        # GitHub Tokenの確認（Wiki更新用）
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            logger.info("環境変数 'GITHUB_TOKEN' が設定されていません。")
            logger.info("Wikiリポジトリの更新にはトークンが必要です。")
        
        # 必須ディレクトリの確認
        if not os.path.exists(os.path.dirname(self.config_path)):
            logger.warning(f"設定ディレクトリが存在しません: {os.path.dirname(self.config_path)}")

    def initialize_components(self):
        """各コンポーネントを初期化する"""
        logger.info("コンポーネントを初期化中...")
        
        try:
            # RSSパーサーの初期化
            self.rss_parser = RSSParser(self.config_path)
            logger.info("RSSパーサーを初期化しました")
            
            # 要約クラスの初期化
            self.summarizer = ArticleSummarizer()
            logger.info("要約クラスを初期化しました")
            
            # Wikiアップデータの初期化
            self.wiki_updater = WikiUpdater(self.wiki_repo_path)
            logger.info("Wikiアップデータを初期化しました")
            
            return True
            
        except Exception as e:
            logger.error(f"コンポーネントの初期化に失敗しました: {e}")
            return False

    def fetch_articles(self) -> List[Dict[str, Any]]:
        """
        RSSフィードから直近24時間の記事を取得する

        Returns:
            List[Dict[str, Any]]: 記事情報のリスト
        """
        logger.info("RSSフィードから記事を取得中...")
        
        try:
            articles = self.rss_parser.fetch_recent_articles()
            logger.info(f"{len(articles)}件の記事を取得しました")
            return articles
            
        except Exception as e:
            logger.error(f"記事の取得中にエラーが発生しました: {e}")
            return []

    def summarize_articles(self, articles: List[Dict[str, Any]]) -> List[str]:
        """
        記事を要約する

        Args:
            articles (List[Dict[str, Any]]): 記事情報のリスト

        Returns:
            List[str]: 要約結果のリスト
        """
        if not articles:
            logger.info("要約する記事がありません")
            return []

        logger.info(f"{len(articles)}件の記事を要約中...")
        
        try:
            summaries = self.summarizer.summarize_multiple_articles(articles)
            logger.info(f"{len(summaries)}件の要約を生成しました")
            return summaries
            
        except Exception as e:
            logger.error(f"要約生成中にエラーが発生しました: {e}")
            return []

    def update_wiki_repository(self, summaries: List[str], wiki_repo_url: str = None) -> bool:
        """
        Wikiリポジトリを更新する

        Args:
            summaries (List[str]): 要約結果のリスト
            wiki_repo_url (str): WikiリポジトリのURL（オプション）

        Returns:
            bool: 成功したかどうか
        """
        logger.info("Wikiリポジトリを更新中...")
        
        try:
            success = self.wiki_updater.update_wiki(summaries, wiki_repo_url)
            
            if success:
                logger.info("Wikiリポジトリの更新に成功しました")
            else:
                logger.error("Wikiリポジトリの更新に失敗しました")
                
            return success
            
        except Exception as e:
            logger.error(f"Wiki更新中にエラーが発生しました: {e}")
            return False

    def run_pipeline(self, wiki_repo_url: str = None) -> bool:
        """
        完全なパイプラインを実行する

        Args:
            wiki_repo_url (str): WikiリポジトリのURL（オプション）

        Returns:
            bool: パイプライン全体が成功したかどうか
        """
        logger.info("=" * 60)
        logger.info("ゲームニュース自動要約システムを開始します")
        logger.info(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # 1. コンポーネントの初期化
        if not self.initialize_components():
            logger.error("コンポーネントの初期化に失敗しました。処理を中止します。")
            return False
        
        # 2. 記事の取得
        articles = self.fetch_articles()
        if not articles:
            logger.warning("取得できる記事がありませんでした。処理を終了します。")
            
            # 記事がなくても空のWikiページを作成する（オプション）
            empty_summaries = []
            self.update_wiki_repository(empty_summaries, wiki_repo_url)
            return True
        
        # 3. 記事の要約
        summaries = self.summarize_articles(articles)
        if not summaries:
            logger.warning("要約を生成できませんでした。処理を終了します。")
            return False
        
        # 4. Wikiリポジトリの更新
        success = self.update_wiki_repository(summaries, wiki_repo_url)
        
        logger.info("=" * 60)
        logger.info("ゲームニュース自動要約システムを完了しました")
        logger.info(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        return success


def main():
    """メインエントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ゲームニュース自動要約システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s                          # 基本設定で実行
  %(prog)s --wiki-url https://github.com/user/repo.wiki.git  # 指定のWikiに更新
  %(prog)s --config custom/feeds.json  # カスタム設定ファイルを使用
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/feeds.json',
        help='RSSフィード設定ファイルのパス（デフォルト: config/feeds.json）'
    )
    
    parser.add_argument(
        '--wiki-path',
        type=str,
        default='wiki',
        help='Wikiリポジトリのローカルパス（デフォルト: wiki）'
    )
    
    parser.add_argument(
        '--wiki-url',
        type=str,
        help='WikiリポジトリのURL（指定した場合、自動クローンされます）'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='テストモードで実行（実際のAPI呼び出しを行わない）'
    )
    
    args = parser.parse_args()
    
    # 環境変数の設定（テストモードの場合）
    if args.test_mode:
        logger.info("テストモードで実行します")
        os.environ['TEST_MODE'] = 'true'
    
    # パイプラインの作成と実行
    pipeline = GameNewsPipeline(
        config_path=args.config,
        wiki_repo_path=args.wiki_path
    )
    
    success = pipeline.run_pipeline(args.wiki_url)
    
    # 終了コードを設定
    if success:
        logger.info("システムは正常に終了しました")
        sys.exit(0)
    else:
        logger.error("システムはエラーで終了しました")
        sys.exit(1)


if __name__ == "__main__":
    main()