#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
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


def parse_json5_like(text: str) -> dict:
    # minimal bridge using node since config is JSON5-ish
    node_code = r'''
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const raw = fs.readFileSync(path, 'utf8');
const obj = vm.runInNewContext('(' + raw + ')');
console.log(JSON.stringify(obj));
'''
    out = subprocess.check_output(['node', '-e', node_code, str(CONFIG_PATH)], text=True)
    return json.loads(out)


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
