"""
sync.py — Git 同步封裝

封裝 portfolio.json / reports/ / memory/ 的 git pull / push 操作。
用於本地跨裝置同步：換電腦後 git clone，每次執行前 pull、執行後 push。

所有操作失敗時只記錄 warning，不中斷主程式（報告生成比同步更重要）。

GitHub Actions 說明：
  GitHub Actions workflow 本身就在 git 環境，由 workflow 最後一步
  直接執行 git push，不需要也不應該透過此模組 push（避免重複 commit）。
  因此在 GitHub Actions 環境中，config.json 的 sync.enabled 應設為 false。
"""

import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

TST = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)

# 只同步這三類，避免意外 commit 敏感或暫存檔案
_STAGED_PATHS = ["reports/", "memory/", "portfolio.json", "thesis/"]


def is_git_repo(repo_dir: Path) -> bool:
    """檢查目錄是否在 git repo 內。"""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def pull(repo_dir: Path) -> bool:
    """
    執行 git pull --rebase。
    回傳 True 表示成功，False 表示失敗（只 log warning，不 raise）。
    """
    if not is_git_repo(repo_dir):
        logger.info("  [sync] 非 git repo，略過 pull")
        return False
    try:
        result = subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info(f"  [sync] git pull 成功：{result.stdout.strip() or 'Already up to date.'}")
            return True
        else:
            logger.warning(f"  [sync] git pull 失敗：{result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        logger.warning("  [sync] git pull 超時（30s）")
        return False
    except Exception as e:
        logger.warning(f"  [sync] git pull 異常：{e}")
        return False


def push(repo_dir: Path, message: str = None) -> bool:
    """
    將 reports/ memory/ portfolio.json 的變動 commit 並 push 到遠端。

    流程：
        1. git add reports/ memory/ portfolio.json
        2. 若 staging area 有變動才 commit（避免空 commit）
        3. git push

    回傳 True 表示成功（含「無變動，略過 commit」情況），
    False 表示 git 操作失敗（只 log warning，不 raise）。
    """
    if not is_git_repo(repo_dir):
        logger.info("  [sync] 非 git repo，略過 push")
        return False

    if message is None:
        today   = datetime.now(TST).strftime("%Y-%m-%d")
        message = f"report: {today}"

    try:
        # Step 1: stage 只限這三類
        subprocess.run(
            ["git", "add"] + _STAGED_PATHS,
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
        )

        # Step 2: 確認 staging area 是否有變動
        diff = subprocess.run(
            ["git", "diff", "--staged", "--quiet"],
            cwd=str(repo_dir),
            capture_output=True,
        )
        if diff.returncode == 0:
            logger.info("  [sync] 無新變動，略過 commit")
            return True

        # Step 3: commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )

        # Step 4: push
        result = subprocess.run(
            ["git", "push"],
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        logger.info(f"  [sync] git push 成功：{message}")
        return True

    except subprocess.CalledProcessError as e:
        logger.warning(f"  [sync] git 操作失敗：{(e.stderr or '').strip()}")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("  [sync] git push 超時（60s）")
        return False
    except Exception as e:
        logger.warning(f"  [sync] git 異常：{e}")
        return False
