#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / 'usage_events.jsonl'


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: record_usage.py <skill-name> [source] [role]', file=sys.stderr)
        return 1

    skill = sys.argv[1].strip()
    if not skill:
        print('skill name required', file=sys.stderr)
        return 1

    source = sys.argv[2].strip() if len(sys.argv) >= 3 else 'runtime-explicit-skill-trigger'
    role = sys.argv[3].strip() if len(sys.argv) >= 4 else 'user-intent'
    source_lower = source.lower()

    if source_lower.startswith('cron-'):
        source_bucket = 'cron'
    elif 'selfcheck' in source_lower or source_lower == 'runtime-explicit-skill-trigger':
        source_bucket = 'selfcheck'
    else:
        source_bucket = 'runtime-explicit'

    role_lower = role.lower()
    if 'user' in role_lower:
        origin_bucket = 'user'
    else:
        origin_bucket = 'assistant'

    event = {
        'skill': skill,
        'event': 'runtime_skill_triggered',
        'source': str(OUT),
        'trigger_source': source,
        'role': role,
        'origin_bucket': origin_bucket,
        'session_scope': 'main',
        'source_bucket': source_bucket,
        'used_at': datetime.now(timezone.utc).isoformat(),
    }

    with OUT.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')

    print(json.dumps({'status': 'ok', 'recorded': event}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
