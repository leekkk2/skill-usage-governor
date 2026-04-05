#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

WORKSPACE = Path('/Users/zhangweiteng/.openclaw/workspace')
SKILL_DIR = WORKSPACE / 'skills' / 'skill-usage-governor'
HOOK_SRC = SKILL_DIR / 'hooks' / 'openclaw'
HOOK_DST = Path('/Users/zhangweiteng/.openclaw/hooks/skill-usage-governor')
CONFIG_PATH = Path('/Users/zhangweiteng/.openclaw/openclaw.json')


def load_config() -> dict:
    node_code = r'''
const fs = require('fs');
const vm = require('vm');
const raw = fs.readFileSync(process.argv[1], 'utf8');
const obj = vm.runInNewContext('(' + raw + ')');
console.log(JSON.stringify(obj));
'''
    out = subprocess.check_output(['node', '-e', node_code, str(CONFIG_PATH)], text=True)
    return json.loads(out)


def to_json5_like(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def main() -> int:
    missing = []
    for path in [SKILL_DIR / 'SKILL.md', HOOK_SRC / 'HOOK.md', HOOK_SRC / 'handler.ts']:
        if not path.exists():
            missing.append(str(path))
    if missing:
        print(json.dumps({'status': 'failed', 'reason': 'missing_source_files', 'missing': missing}, ensure_ascii=False, indent=2))
        return 1

    HOOK_DST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HOOK_SRC / 'HOOK.md', HOOK_DST / 'HOOK.md')
    shutil.copy2(HOOK_SRC / 'handler.ts', HOOK_DST / 'handler.ts')

    cfg = load_config()
    cfg.setdefault('hooks', {})
    cfg['hooks'].setdefault('internal', {})
    cfg['hooks']['internal']['enabled'] = True
    cfg['hooks']['internal'].setdefault('entries', {})
    cfg['hooks']['internal']['entries'].setdefault('skill-usage-governor', {})
    cfg['hooks']['internal']['entries']['skill-usage-governor']['enabled'] = True
    cfg['hooks']['internal'].setdefault('installs', {})
    cfg['hooks']['internal']['installs']['skill-usage-governor'] = {
        'source': 'path',
        'sourcePath': str(HOOK_SRC),
        'installPath': str(HOOK_DST),
        'installedAt': '2026-03-31T16:30:00+08:00',
        'hooks': ['skill-usage-governor'],
    }

    cfg.setdefault('agents', {})
    cfg['agents'].setdefault('list', [])
    for agent in cfg['agents'].get('list', []):
        if agent.get('id') == 'main':
            skills = agent.setdefault('skills', [])
            if 'skill-usage-governor' not in skills:
                skills.append('skill-usage-governor')

    CONFIG_PATH.write_text(to_json5_like(cfg), encoding='utf-8')
    subprocess.check_call(['openclaw', 'gateway', 'restart'])
    subprocess.check_call(['python3', str(SKILL_DIR / 'scripts' / 'check_activation.py')])
    print(json.dumps({'status': 'enabled'}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
