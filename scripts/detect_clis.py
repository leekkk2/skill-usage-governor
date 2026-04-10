#!/usr/bin/env python3
"""自动检测已安装的 vibe coding CLI 及其技能目录。

输出 JSON：
{
  "clis": [
    {"name": "claude-code", "config_dir": "...", "skill_dirs": ["..."], "skills": ["..."]}
  ],
  "all_skill_dirs": ["..."],
  "all_skills": {"skill-name": {"source": "claude-code", "dir": "..."}}
}
"""
import json
import os
import platform
import shutil
import sys
from pathlib import Path

# ── 跨平台基础路径 ──────────────────────────────────────────────

IS_WINDOWS = platform.system() == 'Windows'
HOME = Path.home()
APPDATA = Path(os.environ.get('APPDATA', '')) if IS_WINDOWS else None
LOCALAPPDATA = Path(os.environ.get('LOCALAPPDATA', '')) if IS_WINDOWS else None


def _candidates(*parts_list):
    """为同一 CLI 返回多个候选配置目录（跨平台）。"""
    dirs = []
    for parts in parts_list:
        dirs.append(HOME.joinpath(*parts))
    if IS_WINDOWS and APPDATA and APPDATA.exists():
        for parts in parts_list:
            candidate = APPDATA.joinpath(*parts)
            if candidate not in dirs:
                dirs.append(candidate)
    if IS_WINDOWS and LOCALAPPDATA and LOCALAPPDATA.exists():
        for parts in parts_list:
            candidate = LOCALAPPDATA.joinpath(*parts)
            if candidate not in dirs:
                dirs.append(candidate)
    return dirs


# ── CLI 定义 ─────────────────────────────────────────────────────

IGNORE_PREFIXES = ('zz-', 'tmp-', 'test-', 'e2e-')
IGNORE_NAMES = set()


def _is_ignored(name: str) -> bool:
    if name in IGNORE_NAMES:
        return True
    return any(name.startswith(p) for p in IGNORE_PREFIXES)


def _scan_skills_in_dir(d: Path) -> list[str]:
    """扫描目录下含 SKILL.md 的子目录，返回技能名列表。"""
    if not d.exists():
        return []
    results = []
    try:
        for p in sorted(d.iterdir()):
            if p.is_dir() and (p / 'SKILL.md').exists() and not _is_ignored(p.name):
                results.append(p.name)
    except PermissionError:
        pass
    return results


def _scan_plugins_recursive(base: Path, max_depth: int = 6) -> list[Path]:
    """递归查找插件缓存中包含 SKILL.md 的 skills/ 目录。"""
    found = []
    if not base.exists():
        return found
    try:
        for skills_dir in base.rglob('skills'):
            if not skills_dir.is_dir():
                continue
            # 限制深度
            try:
                skills_dir.relative_to(base)
            except ValueError:
                continue
            depth = len(skills_dir.relative_to(base).parts)
            if depth > max_depth:
                continue
            # 至少有一个子目录含 SKILL.md
            has_skill = any(
                (child / 'SKILL.md').exists()
                for child in skills_dir.iterdir()
                if child.is_dir()
            )
            if has_skill:
                found.append(skills_dir)
    except PermissionError:
        pass
    return found


def detect_openclaw() -> dict | None:
    config_candidates = _candidates(('.openclaw',),)
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        skills_path = config_dir / 'workspace' / 'skills'
        if skills_path.exists():
            skill_dirs.append(str(skills_path))
        return {
            'name': 'openclaw',
            'config_dir': str(config_dir),
            'skill_dirs': skill_dirs,
        }
    return None


def detect_claude_code() -> dict | None:
    config_candidates = _candidates(('.claude',),)
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        # 用户级技能
        user_skills = config_dir / 'skills'
        if user_skills.exists():
            skill_dirs.append(str(user_skills))
        # 插件缓存中的技能
        plugins_cache = config_dir / 'plugins' / 'cache'
        for plugin_skills in _scan_plugins_recursive(plugins_cache):
            skill_dirs.append(str(plugin_skills))
        # 插件 marketplace 中的技能
        plugins_market = config_dir / 'plugins' / 'marketplaces'
        for plugin_skills in _scan_plugins_recursive(plugins_market):
            skill_dirs.append(str(plugin_skills))
        return {
            'name': 'claude-code',
            'config_dir': str(config_dir),
            'skill_dirs': skill_dirs,
        }
    return None


def detect_gemini() -> dict | None:
    config_candidates = _candidates(('.gemini',),)
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        for sub in ('skills', 'extensions'):
            p = config_dir / sub
            if p.exists():
                skill_dirs.append(str(p))
        # Gemini 插件缓存
        plugins_cache = config_dir / 'plugins' / 'cache'
        for plugin_skills in _scan_plugins_recursive(plugins_cache):
            skill_dirs.append(str(plugin_skills))
        return {
            'name': 'gemini',
            'config_dir': str(config_dir),
            'skill_dirs': skill_dirs,
        }
    return None


def detect_windsurf() -> dict | None:
    config_candidates = _candidates(('.windsurf',), ('.codeium',))
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        for sub in ('skills',):
            p = config_dir / sub
            if p.exists():
                skill_dirs.append(str(p))
        # Windsurf 子目录中的技能
        windsurf_sub = config_dir / 'windsurf' / 'skills'
        if windsurf_sub.exists():
            skill_dirs.append(str(windsurf_sub))
        if skill_dirs:
            return {
                'name': 'windsurf',
                'config_dir': str(config_dir),
                'skill_dirs': skill_dirs,
            }
    return None


def detect_cursor() -> dict | None:
    config_candidates = _candidates(('.cursor',),)
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        for sub in ('skills',):
            p = config_dir / sub
            if p.exists():
                skill_dirs.append(str(p))
        if skill_dirs:
            return {
                'name': 'cursor',
                'config_dir': str(config_dir),
                'skill_dirs': skill_dirs,
            }
    return None


def detect_codex() -> dict | None:
    config_candidates = _candidates(('.codex',),)
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        skills_path = config_dir / 'skills'
        if skills_path.exists():
            skill_dirs.append(str(skills_path))
        return {
            'name': 'codex',
            'config_dir': str(config_dir),
            'skill_dirs': skill_dirs,
        }
    return None


def detect_aider() -> dict | None:
    config_candidates = _candidates(('.aider',),)
    for config_dir in config_candidates:
        if not config_dir.exists():
            continue
        skill_dirs = []
        skills_path = config_dir / 'skills'
        if skills_path.exists():
            skill_dirs.append(str(skills_path))
        if skill_dirs:
            return {
                'name': 'aider',
                'config_dir': str(config_dir),
                'skill_dirs': skill_dirs,
            }
    return None


DETECTORS = [
    detect_openclaw,
    detect_claude_code,
    detect_gemini,
    detect_windsurf,
    detect_cursor,
    detect_codex,
    detect_aider,
]


def detect_all(extra_dirs: list[str] | None = None) -> dict:
    """检测所有已安装 CLI，汇总技能目录和技能列表。"""
    clis = []
    all_skill_dirs = []
    all_skills = {}
    seen_dirs = set()

    for detector in DETECTORS:
        result = detector()
        if result is None:
            continue
        cli_skills = []
        for d_str in result['skill_dirs']:
            d = Path(d_str)
            resolved = str(d.resolve())
            if resolved in seen_dirs:
                continue
            seen_dirs.add(resolved)
            all_skill_dirs.append(d_str)
            for skill_name in _scan_skills_in_dir(d):
                if skill_name not in all_skills:
                    all_skills[skill_name] = {
                        'source': result['name'],
                        'dir': d_str,
                    }
                cli_skills.append(skill_name)
        result['skills'] = sorted(set(cli_skills))
        clis.append(result)

    # 额外手动指定的目录（输入校验：限制数量和路径长度）
    MAX_EXTRA_DIRS = 20
    MAX_PATH_LEN = 1024
    if extra_dirs:
        for d_str in extra_dirs[:MAX_EXTRA_DIRS]:
            if len(d_str) > MAX_PATH_LEN:
                continue
            d = Path(d_str).expanduser()
            resolved = str(d.resolve())
            if resolved in seen_dirs or not d.exists():
                continue
            seen_dirs.add(resolved)
            all_skill_dirs.append(str(d))
            for skill_name in _scan_skills_in_dir(d):
                if skill_name not in all_skills:
                    all_skills[skill_name] = {
                        'source': 'extra',
                        'dir': str(d),
                    }

    return {
        'platform': platform.system(),
        'clis': clis,
        'all_skill_dirs': all_skill_dirs,
        'all_skills': all_skills,
    }


if __name__ == '__main__':
    extra = []
    if len(sys.argv) > 1:
        extra = sys.argv[1:]
    result = detect_all(extra)
    print(json.dumps(result, ensure_ascii=False, indent=2))
