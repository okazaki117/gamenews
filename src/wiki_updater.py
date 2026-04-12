import os
import subprocess
import datetime
from typing import List
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WikiUpdater:
    """要約データをMarkdownファイルに変換し、GitHub Wikiリポジトリにプッシュするクラス"""

    def __init__(self, wiki_repo_path: str = "wiki"):
        """
        Wikiアップデータの初期化

        Args:
            wiki_repo_path (str): Wikiリポジトリのローカルパス
        """
        self.wiki_repo_path = wiki_repo_path
        self.today = datetime.datetime.now()

    def _run_git_command(self, command: str, cwd: str = None) -> tuple:
        """
        Gitコマンドを実行する

        Args:
            command (str): 実行するGitコマンド
            cwd (str): 作業ディレクトリ（Noneの場合はwiki_repo_path）

        Returns:
            tuple: (成功フラグ, 出力メッセージ)
        """
        if cwd is None:
            cwd = self.wiki_repo_path

        try:
            logger.info(f"Gitコマンドを実行: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            if result.returncode == 0:
                logger.info(f"Gitコマンド成功: {command}")
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Gitコマンド失敗: {command}")
                logger.error(f"エラー詳細: {error_msg}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Gitコマンド実行エラー: {command}")
            logger.error(f"例外: {e}")
            return False, str(e)

    def configure_git_user(self, username: str = "github-actions[bot]", 
                          email: str = "github-actions[bot]@users.noreply.github.com") -> bool:
        """
        Gitユーザー設定を行う

        Args:
            username (str): Gitユーザー名
            email (str): Gitメールアドレス

        Returns:
            bool: 成功したかどうか
        """
        # ユーザー名設定
        success1, _ = self._run_git_command(f'git config user.name "{username}"')
        
        # メールアドレス設定
        success2, _ = self._run_git_command(f'git config user.email "{email}"')
        
        return success1 and success2

    def generate_markdown_content(self, summaries: List[str]) -> str:
        """
        要約データからMarkdownコンテンツを生成する

        Args:
            summaries (List[str]): 要約データのリスト

        Returns:
            str: 生成されたMarkdownコンテンツ
        """
        date_str = self.today.strftime("%Y年%m月%d日 (%A)")
        jst_date = self.today.strftime("%Y-%m-%d")
        
        markdown_content = f"""# ゲームビジネスニュース要約 {date_str}

このページは自動生成されたゲームビジネスニュースの要約です。
最新のゲーム業界ニュースをAI（DeepSeek）が要約し、毎日更新しています。

## 概要
- **取得日時**: {jst_date} (JST)
- **要約記事数**: {len(summaries)}件
- **生成方法**: RSSフィードから直近24時間の記事を取得し、AIで要約

---

"""

        if not summaries:
            markdown_content += """## 本日の記事
本日は直近24時間以内の新しい記事がありませんでした。

---
"""
        else:
            markdown_content += "## 記事要約\n\n"
            for summary in summaries:
                markdown_content += summary + "\n\n"

        # フッター情報
        markdown_content += f"""## システム情報
- **最終更新**: {self.today.strftime("%Y-%m-%d %H:%M:%S JST")}
- **生成システム**: RSS自動取得・AI要約システム
- **実行環境**: GitHub Actions (Ubuntu)
- **AIモデル**: DeepSeek Chat

---
> このページは自動生成されています。元記事の正確性については各ニュースソースを参照してください。
"""
        
        return markdown_content

    def create_markdown_file(self, markdown_content: str) -> str:
        """
        Markdownファイルを作成する

        Args:
            markdown_content (str): Markdownコンテンツ

        Returns:
            str: 作成されたファイルのパス
        """
        # ファイル名を生成（例: GameNews_20250412.md）
        filename = f"GameNews_{self.today.strftime('%Y%m%d')}.md"
        filepath = os.path.join(self.wiki_repo_path, filename)
        
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(self.wiki_repo_path, exist_ok=True)
            
            # ファイルを書き込み
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Markdownファイルを作成しました: {filepath}")
            logger.info(f"ファイルサイズ: {len(markdown_content)} 文字")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Markdownファイル作成エラー: {e}")
            raise

    def clone_wiki_repository(self, wiki_repo_url: str, wiki_token: str = None) -> bool:
        """
        Wikiリポジトリをクローンする

        Args:
            wiki_repo_url (str): WikiリポジトリのURL
            wiki_token (str): プライベートリポジトリ用のトークン

        Returns:
            bool: 成功したかどうか
        """
        try:
            # 既存ディレクトリを削除（クリーンな状態から開始）
            if os.path.exists(self.wiki_repo_path):
                logger.info(f"既存のディレクトリを削除: {self.wiki_repo_path}")
                import shutil
                shutil.rmtree(self.wiki_repo_path, ignore_errors=True)

            # URLにトークンを組み込む（必要な場合）
            if wiki_token and "github.com" in wiki_repo_url:
                # https://github.com/username/repo.wiki.git → https://x-access-token:token@github.com/username/repo.wiki.git
                auth_url = wiki_repo_url.replace("https://", f"https://x-access-token:{wiki_token}@")
                clone_url = auth_url
            else:
                clone_url = wiki_repo_url

            logger.info(f"Wikiリポジトリをクローン: {wiki_repo_url}")
            
            # Gitクローンコマンドを実行
            success, output = self._run_git_command(
                f'git clone {clone_url} "{self.wiki_repo_path}"',
                cwd="."  # カレントディレクトリから実行
            )
            
            if success:
                logger.info(f"Wikiリポジトリのクローンに成功: {self.wiki_repo_path}")
                return True
            else:
                logger.error(f"Wikiリポジトリのクローンに失敗: {output}")
                return False
                
        except Exception as e:
            logger.error(f"Wikiリポジトリクローンエラー: {e}")
            return False

    def update_wiki(self, summaries: List[str], wiki_repo_url: str = None) -> bool:
        """
        要約データをWikiリポジトリにプッシュする

        Args:
            summaries (List[str]): 要約データのリスト
            wiki_repo_url (str): WikiリポジトリURL（指定された場合のみクローン）

        Returns:
            bool: 成功したかどうか
        """
        try:
            # 1. 必要に応じてWikiリポジトリをクローン
            if wiki_repo_url:
                logger.info("Wikiリポジトリをクローンします")
                
                # GitHub Tokenを環境変数から取得
                github_token = os.environ.get("GITHUB_TOKEN")
                
                if not self.clone_wiki_repository(wiki_repo_url, github_token):
                    logger.error("Wikiリポジトリのクローンに失敗しました")
                    return False
            else:
                logger.info("既存のWikiリポジトリを使用します")
                if not os.path.exists(self.wiki_repo_path):
                    logger.error(f"Wikiリポジトリパスが存在しません: {self.wiki_repo_path}")
                    return False

            # 2. Gitユーザー設定
            logger.info("Gitユーザー設定を行います")
            if not self.configure_git_user():
                logger.warning("Gitユーザー設定に失敗しましたが、処理を続行します")

            # 3. Markdownコンテンツ生成
            logger.info("Markdownコンテンツを生成します")
            markdown_content = self.generate_markdown_content(summaries)

            # 4. Markdownファイル作成
            logger.info("Markdownファイルを作成します")
            filepath = self.create_markdown_file(markdown_content)

            # 5. Git操作: add
            logger.info("変更をステージングします")
            success_add, _ = self._run_git_command("git add .")
            if not success_add:
                logger.error("git add に失敗しました")
                return False

            # 6. Git操作: commit
            commit_message = f"docs: Auto update daily game news ({self.today.strftime('%Y-%m-%d')})"
            logger.info(f"コミットを実行: {commit_message}")
            success_commit, commit_output = self._run_git_command(f'git commit -m "{commit_message}"')
            
            if not success_commit:
                # 変更がない場合のコミット失敗は無視
                if "nothing to commit" in commit_output.lower():
                    logger.info("コミットする変更がありません")
                    return True
                else:
                    logger.error(f"git commit に失敗: {commit_output}")
                    return False

            # 7. Git操作: push
            logger.info("リポジトリにプッシュします")
            success_push, push_output = self._run_git_command("git push")
            
            if success_push:
                logger.info("Wikiの更新に成功しました")
                return True
            else:
                logger.error(f"git push に失敗: {push_output}")
                return False

        except Exception as e:
            logger.error(f"Wiki更新処理中にエラーが発生しました: {e}")
            return False


def main():
    """テスト用のメイン関数"""
    # テスト用の要約データ
    test_summaries = [
        """## ゲーム業界の最新動向

**出典**: テストフィード | [元記事](https://example.com/article1)

### 要点
- モバイルゲーム市場が継続的に拡大、特にアジア地域で成長が顕著
- 新興企業のイノベーションと既存大手企業の戦略転換が同時進行
- クラウドゲーミングやメタバース関連技術への投資が活発化

---""",
        """## AIを活用したゲーム開発ツールが増加

**出典**: ゲーム開発ニュース | [元記事](https://example.com/article2)

### 要点
- ゲーム開発におけるAIツールの採用が加速
- 自動テストやバグ検出、コンテンツ生成など多様な用途に展開
- 開発コスト削減と品質向上の両立を実現

---"""
    ]

    # Wikiアップデータのインスタンス作成
    updater = WikiUpdater(wiki_repo_path="test_wiki")

    # Markdownコンテンツ生成テスト
    logger.info("Markdownコンテンツ生成テスト")
    markdown_content = updater.generate_markdown_content(test_summaries)
    
    print("生成されたMarkdownコンテンツ（先頭500文字）:")
    print(markdown_content[:500] + "...")
    print(f"\n全体の長さ: {len(markdown_content)} 文字")
    
    # ファイル作成テスト（環境に依存しないように仮想パス）
    try:
        os.makedirs("test_wiki", exist_ok=True)
        filepath = updater.create_markdown_file(markdown_content)
        print(f"テストファイルを作成しました: {filepath}")
        
        # テスト後にクリーンアップ
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists("test_wiki"):
            os.rmdir("test_wiki")
            
    except Exception as e:
        print(f"ファイル操作テストでエラーが発生しました（正常）: {e}")


if __name__ == "__main__":
    main()