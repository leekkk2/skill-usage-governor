#!/usr/bin/env python3
"""skill-usage-governor 自更新脚本。

用法：
  python3 scripts/update.py --check     # 仅检查是否有更新
  python3 scripts/update.py --apply     # 拉取并应用更新
  python3 scripts/update.py --source <path-or-url>  # 指定自定义更新源

更新策略：
  1. 如果当前技能目录本身是 git 仓库 → git pull
  2. 如果有已知的 git 远程源 → clone 到临时目录，diff 后覆盖
  3. 如果指定了 --source → 从该路径/URL 拉取

安全：
  - --check 不做任何修改
  - --apply 先备份再更新
  - 支持 --dry-run 查看变更但不应用
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
DATA.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = DATA / 'update_backups'

# 已知的技能安装位置（按优先级）
KNOWN_INSTALL_LOCATIONS = [
    Path.home() / '.openclaw' / 'workspace' / 'skills' / 'skill-usage-governor',
    Path.home() / '.claude' / 'skills' / 'skill-usage-governor',
    Path.home() / '.codex' / 'skills' / 'skill-usage-governor',
    Path.home() / '.gemini' / 'skills' / 'skill-usage-governor',
    Path.home() / '.cursor' / 'skills' / 'skill-usage-governor',
]

DEFAULT_REMOTE = 'https://github.com/leekkk2/skill-usage-governor.git'

parser = argparse.ArgumentParser(description='skill-usage-governor 自更新')
parser.add_argument('--check', action='store_true', help='仅检查是否有更新')
parser.add_argument('--apply', action='store_true', help='拉取并应用更新')
parser.add_argument('--dry-run', action='store_true', help='查看变更但不应用')
parser.add_argument('--source', type=str, default=None, help='自定义更新源（本地路径或 git URL）')
parser.add_argument('--branch', type=str, default='main', help='远程分支名（默认 main）')
parser.add_argument(
    '--confirm-remote', action='store_true',
    help='确认从远程仓库拉取并覆盖本地脚本（安全门禁：无本地 git 仓库时必须显式指定）',
)
args = parser.parse_args()

if not args.check and not args.apply:
    parser.print_help()
    raise SystemExit(1)


def find_git_root(path: Path) -> Path | None:
    """查找 path 所在的 git 仓库根目录。"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, cwd=str(path),
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


def get_local_commit(git_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=str(git_dir),
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_remote_commit(git_dir: Path, branch: str) -> str | None:
    try:
        subprocess.run(
            ['git', 'fetch', 'origin', branch, '--quiet'],
            capture_output=True, text=True, cwd=str(git_dir), timeout=30,
        )
        result = subprocess.run(
            ['git', 'rev-parse', f'origin/{branch}'],
            capture_output=True, text=True, cwd=str(git_dir),
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_diff_summary(git_dir: Path, branch: str) -> str:
    try:
        result = subprocess.run(
            ['git', 'diff', '--stat', f'HEAD...origin/{branch}'],
            capture_output=True, text=True, cwd=str(git_dir),
        )
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''


def get_log_summary(git_dir: Path, local_commit: str, branch: str) -> str:
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', f'{local_commit}..origin/{branch}'],
            capture_output=True, text=True, cwd=str(git_dir),
        )
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''


def find_primary_install() -> Path | None:
    """找到主安装位置（含 .git 的优先）。"""
    git_locations = []
    non_git_locations = []
    for loc in KNOWN_INSTALL_LOCATIONS:
        if not loc.exists():
            continue
        if (loc / '.git').exists() or find_git_root(loc) == loc:
            git_locations.append(loc)
        else:
            non_git_locations.append(loc)
    return (git_locations + non_git_locations + [None])[0]


def backup_current(target: Path) -> Path:
    """备份当前版本到 data/update_backups/。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_path = BACKUP_DIR / ts
    shutil.copytree(target, backup_path, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
    return backup_path


def sync_to_copies(source: Path):
    """将更新后的文件同步到所有已知安装位置。"""
    source_resolved = source.resolve()
    synced = []
    for loc in KNOWN_INSTALL_LOCATIONS + [BASE]:
        loc_resolved = loc.resolve()
        if not loc.exists() or loc_resolved == source_resolved:
            continue
        # 只同步 scripts/ config/ hooks/ SKILL.md README.md
        for item in ('scripts', 'config', 'hooks', 'SKILL.md', 'README.md'):
            src = source / item
            dst = loc / item
            if not src.exists():
                continue
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        synced.append(str(loc))
    return synced


# ── 主流程 ──────────────────────────────────────────────────────

primary = find_primary_install()
source_override = args.source

if source_override:
    source_path = Path(source_override).expanduser()
    if source_path.exists() and source_path.is_dir():
        # 本地目录作为源
        print(f'更新源：本地目录 {source_path}')
        if args.check:
            print('本地源不支持 --check，请使用 --apply')
            raise SystemExit(0)
        if args.apply and not args.dry_run:
            backup = backup_current(BASE)
            print(f'已备份当前版本 → {backup}')
            synced = sync_to_copies(source_path)
            # 也同步到 BASE
            for item in ('scripts', 'config', 'hooks', 'SKILL.md', 'README.md'):
                src = source_path / item
                dst = BASE / item
                if not src.exists():
                    continue
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            print(f'已更新 {BASE}')
            if synced:
                print(f'已同步到：{", ".join(synced)}')
        raise SystemExit(0)
    else:
        # 当作 git URL
        print(f'更新源：git {source_override}')

if primary and (primary / '.git').exists():
    git_dir = primary
    print(f'检测到 git 仓库：{git_dir}')
    local = get_local_commit(git_dir)
    remote = get_remote_commit(git_dir, args.branch)

    if not local or not remote:
        print('无法获取本地或远程 commit，请检查网络和 git 配置')
        raise SystemExit(1)

    if local == remote:
        print(f'已是最新版本 ({local[:8]})')
        raise SystemExit(0)

    print(f'本地版本：{local[:8]}')
    print(f'远程版本：{remote[:8]}')
    log = get_log_summary(git_dir, local, args.branch)
    if log:
        print(f'\n新提交：\n{log}')
    diff = get_diff_summary(git_dir, args.branch)
    if diff:
        print(f'\n变更摘要：\n{diff}')

    if args.check:
        print('\n有可用更新。运行 --apply 来应用。')
        raise SystemExit(0)

    if args.dry_run:
        print('\ndry-run 模式，不做实际变更。')
        raise SystemExit(0)

    # 执行更新
    backup = backup_current(git_dir)
    print(f'\n已备份 → {backup}')

    result = subprocess.run(
        ['git', 'pull', 'origin', args.branch],
        capture_output=True, text=True, cwd=str(git_dir),
    )
    if result.returncode != 0:
        print(f'git pull 失败：{result.stderr}')
        raise SystemExit(1)
    print(f'git pull 成功')

    new_commit = get_local_commit(git_dir)
    print(f'更新后版本：{new_commit[:8] if new_commit else "unknown"}')

    # 同步到其他安装位置
    synced = sync_to_copies(git_dir)
    if synced:
        print(f'已同步到：{", ".join(synced)}')
    print('更新完成！')

else:
    # 没有 git 仓库，尝试 clone 到临时目录再同步
    remote_url = source_override or DEFAULT_REMOTE
    print(f'无本地 git 仓库，从远程拉取：{remote_url}')

    if args.check:
        print('无法对比版本（无本地 git 历史）。运行 --apply --confirm-remote 直接拉取最新版本。')
        raise SystemExit(0)

    if args.dry_run:
        print('dry-run 模式：将从远程克隆并覆盖当前安装。')
        raise SystemExit(0)

    # 安全门禁：从远程拉取并覆盖本地脚本，必须显式确认
    if not args.confirm_remote:
        print(
            '⚠️  安全提示：即将从远程仓库下载代码并覆盖本地 scripts/ config/ hooks/ 目录。\n'
            f'   远程源：{remote_url}\n'
            f'   分支：{args.branch}\n'
            '   这将替换当前安装的脚本文件。\n'
            '\n'
            '如果确认要执行，请添加 --confirm-remote 参数：\n'
            f'   python3 scripts/update.py --apply --confirm-remote'
        )
        raise SystemExit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ['git', 'clone', '--depth=1', '--branch', args.branch, remote_url, tmpdir],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f'git clone 失败：{result.stderr}')
            raise SystemExit(1)

        # 显示即将应用的 commit hash
        commit_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=tmpdir,
        )
        commit_hash = commit_result.stdout.strip() if commit_result.returncode == 0 else 'unknown'
        print(f'远程版本 commit：{commit_hash}')

        backup = backup_current(BASE)
        print(f'已备份 → {backup}')

        tmp_path = Path(tmpdir)
        for item in ('scripts', 'config', 'hooks', 'SKILL.md', 'README.md'):
            src = tmp_path / item
            dst = BASE / item
            if not src.exists():
                continue
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        print(f'已更新 {BASE}')

        if primary and primary.resolve() != BASE.resolve():
            synced = sync_to_copies(tmp_path)
            if synced:
                print(f'已同步到：{", ".join(synced)}')

    print('更新完成！')
