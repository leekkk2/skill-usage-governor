#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

_DEFAULT_OPENCLAW = Path.home() / '.openclaw'
_OPENCLAW_DIR = Path(os.environ.get('OPENCLAW_CONFIG_DIR', str(_DEFAULT_OPENCLAW)))
WORKSPACE = Path(os.environ.get('WORKSPACE', str(_OPENCLAW_DIR / 'workspace')))
SKILL_DIR = WORKSPACE / 'skills' / 'skill-usage-governor'
HOOK_SRC = SKILL_DIR / 'hooks' / 'openclaw'
HOOK_DST = Path(os.environ.get('OPENCLAW_HOOKS_DIR', str(_OPENCLAW_DIR / 'hooks'))) / 'skill-usage-governor'
CONFIG_PATH = Path(os.environ.get('OPENCLAW_CONFIG_FILE', str(_OPENCLAW_DIR / 'openclaw.json')))

CHECKS = []


def add_check(name: str, ok: bool, detail: str = '') -> None:
    CHECKS.append({'name': name, 'ok': ok, 'detail': detail})


def _strip_json5_extras(text: str) -> str:
    """安全地将 JSON5 风格文本转换为标准 JSON（去除注释和尾逗号）"""
    import re as _re
    # 去除单行注释（// ...），但不影响字符串内的 //
    result = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"' and not in_string:
            in_string = True
            result.append(ch)
            i += 1
            continue
        if ch == '"' and in_string:
            in_string = False
            result.append(ch)
            i += 1
            continue
        if not in_string and ch == '/' and i + 1 < len(text) and text[i + 1] == '/':
            # 跳过到行尾
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        if not in_string and ch == '/' and i + 1 < len(text) and text[i + 1] == '*':
            # 跳过块注释
            i += 2
            while i + 1 < len(text) and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
            continue
        result.append(ch)
        i += 1
    cleaned = ''.join(result)
    # 去除尾逗号 (}, 或 ],)
    cleaned = _re.sub(r',\s*([}\]])', r'\1', cleaned)
    return cleaned


def parse_json5_like(text: str) -> dict:
    # 安全的纯 Python 解析：去除注释和尾逗号后用标准 json.loads
    raw = Path(CONFIG_PATH).read_text(encoding='utf-8')
    cleaned = _strip_json5_extras(raw)
    return json.loads(cleaned)


def main() -> int:
    add_check('SKILL.md exists', (SKILL_DIR / 'SKILL.md').exists(), str(SKILL_DIR / 'SKILL.md'))
    add_check('hook source HOOK.md exists', (HOOK_SRC / 'HOOK.md').exists(), str(HOOK_SRC / 'HOOK.md'))
    add_check('hook source handler.ts exists', (HOOK_SRC / 'handler.ts').exists(), str(HOOK_SRC / 'handler.ts'))

    cfg = parse_json5_like(CONFIG_PATH)
    hooks_internal = (((cfg.get('hooks') or {}).get('internal')) or {})
    entries = hooks_internal.get('entries') or {}
    installs = hooks_internal.get('installs') or {}

    add_check('hooks.internal.enabled == true', bool(hooks_internal.get('enabled')) is True, str(hooks_internal.get('enabled')))
    add_check(
        'hooks.internal.entries.skill-usage-governor.enabled == true',
        bool((((entries.get('skill-usage-governor') or {}).get('enabled')))) is True,
        json.dumps(entries.get('skill-usage-governor', {}), ensure_ascii=False),
    )
    install_rec = installs.get('skill-usage-governor') or {}
    add_check('install record exists', bool(install_rec), json.dumps(install_rec, ensure_ascii=False))
    add_check('installPath exists', HOOK_DST.exists(), str(HOOK_DST))
    add_check('runtime HOOK.md exists', (HOOK_DST / 'HOOK.md').exists(), str(HOOK_DST / 'HOOK.md'))
    add_check('runtime handler.ts exists', (HOOK_DST / 'handler.ts').exists(), str(HOOK_DST / 'handler.ts'))

    ok = all(item['ok'] for item in CHECKS)
    result = {
        'status': 'enabled' if ok else 'not_enabled',
        'checks': CHECKS,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
