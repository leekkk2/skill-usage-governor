#!/usr/bin/env python3
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
WORKSPACE = BASE.parents[1]
SKILLS_DIR = WORKSPACE / 'skills'
DATA = BASE / 'data'
CONFIG = BASE / 'config'
events = DATA / 'usage_events.jsonl'
stats = DATA / 'usage_stats.json'
report = DATA / 'report-latest.md'
policy_file = CONFIG / 'policy.yaml'
NOW = datetime.now(timezone.utc)


IGNORE_PREFIXES = ('zz-', 'tmp-', 'test-', 'e2e-')


def is_ignored_skill_dir(path: Path) -> bool:
    name = path.name
    return any(name.startswith(prefix) for prefix in IGNORE_PREFIXES)


ALL_SKILLS = sorted([
    p.name for p in SKILLS_DIR.iterdir()
    if p.is_dir() and (p / 'SKILL.md').exists() and not is_ignored_skill_dir(p)
]) if SKILLS_DIR.exists() else []

ACTIVATION_EVENTS = {
    'skill_activation_detected',
    'runtime_skill_triggered',
}

MENTION_EVENTS = {
    'skill_reference_detected',
    'skill_mentioned',
}


def load_policy() -> dict:
    policy = {}
    current_section = None
    if not policy_file.exists():
        return policy

    with policy_file.open('r', encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if not line.startswith(' '):
                current_section = None
                if stripped.endswith(':'):
                    current_section = stripped[:-1]
                    policy[current_section] = None
                    continue
                if ':' not in stripped:
                    continue
                key, value = stripped.split(':', 1)
                policy[key.strip()] = value.strip()
                continue
            if current_section is None:
                continue
            if stripped.startswith('- '):
                if not isinstance(policy[current_section], list):
                    policy[current_section] = []
                policy[current_section].append(stripped[2:].strip())
                continue
            if ':' not in stripped:
                continue
            if not isinstance(policy[current_section], dict):
                policy[current_section] = {}
            key, value = stripped.split(':', 1)
            policy[current_section][key.strip()] = value.strip()
    return policy


def parse_timestamp(value: str):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


items = []
if events.exists():
    with events.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

policy = load_policy()
weights = policy.get('weights', {}) if isinstance(policy.get('weights'), dict) else {}
weight_30d = float(weights.get('uses_30d', 0.55) or 0.55)
weight_7d = float(weights.get('uses_7d', 0.30) or 0.30)
weight_total = float(weights.get('total_uses', 0.0) or 0.0)
weight_recency = float(weights.get('recency', 0.15) or 0.15)
activation_weights = policy.get('activation_weights', {}) if isinstance(policy.get('activation_weights'), dict) else {}
activation_bonus = float(activation_weights.get('activation_bonus', 5.0) or 5.0)
activation_30d_bonus = float(activation_weights.get('activation_30d_bonus', 3.0) or 3.0)
activation_7d_bonus = float(activation_weights.get('activation_7d_bonus', 2.0) or 2.0)

by_skill = {
    skill: {
        'skill': skill,
        'total_uses': 0,
        'uses_7d': 0,
        'uses_30d': 0,
        'activation_total_uses': 0,
        'activation_uses_7d': 0,
        'activation_uses_30d': 0,
        'activation_by_source_bucket': {},
        'mention_by_source_bucket': {},
        'days_since_last_used': None,
        'last_used_at': None,
        'last_activated_at': None,
        'last_mentioned_at': None,
        '_last_used_rank': (0, 0),
        'score': 0.0,
    }
    for skill in ALL_SKILLS
}

for item in items:
    skill = item.get('skill')
    used_at = item.get('used_at')
    event_type = item.get('event')
    source_bucket = item.get('source_bucket') or 'unknown'
    if not isinstance(skill, str) or not skill.strip() or skill not in by_skill:
        continue
    dt = parse_timestamp(used_at)
    if dt is None:
        continue
    candidate_rank = (1, int(dt.timestamp()))
    slot = by_skill[skill]
    if event_type in ACTIVATION_EVENTS:
        slot['activation_total_uses'] += 1
        slot['activation_by_source_bucket'][source_bucket] = slot['activation_by_source_bucket'].get(source_bucket, 0) + 1
        if dt >= NOW - timedelta(days=7):
            slot['activation_uses_7d'] += 1
        if dt >= NOW - timedelta(days=30):
            slot['activation_uses_30d'] += 1
        if slot['last_activated_at'] is None or dt >= parse_timestamp(slot['last_activated_at']):
            slot['last_activated_at'] = used_at
    elif event_type in MENTION_EVENTS:
        slot['total_uses'] += 1
        slot['mention_by_source_bucket'][source_bucket] = slot['mention_by_source_bucket'].get(source_bucket, 0) + 1
        if dt >= NOW - timedelta(days=7):
            slot['uses_7d'] += 1
        if dt >= NOW - timedelta(days=30):
            slot['uses_30d'] += 1
        if slot['last_mentioned_at'] is None or dt >= parse_timestamp(slot['last_mentioned_at']):
            slot['last_mentioned_at'] = used_at
    else:
        continue

    should_update_last_used = False
    if event_type in ACTIVATION_EVENTS:
        should_update_last_used = True
    elif slot['activation_total_uses'] == 0:
        should_update_last_used = True

    if should_update_last_used:
        if candidate_rank > slot['_last_used_rank']:
            slot['_last_used_rank'] = candidate_rank
            slot['last_used_at'] = used_at
        elif candidate_rank == slot['_last_used_rank'] and slot['last_used_at'] and used_at > slot['last_used_at']:
            slot['last_used_at'] = used_at
        elif candidate_rank == slot['_last_used_rank'] and slot['last_used_at'] is None:
            slot['last_used_at'] = used_at

max_30d = max((row['uses_30d'] for row in by_skill.values()), default=0)
max_7d = max((row['uses_7d'] for row in by_skill.values()), default=0)
max_total = max((row['total_uses'] for row in by_skill.values()), default=0)
max_activation_30d = max((row['activation_uses_30d'] for row in by_skill.values()), default=0)
max_activation_7d = max((row['activation_uses_7d'] for row in by_skill.values()), default=0)
max_activation_total = max((row['activation_total_uses'] for row in by_skill.values()), default=0)
for row in by_skill.values():
    last_dt = parse_timestamp(row['last_used_at'])
    days_since_last_used = (NOW - last_dt).total_seconds() / 86400 if last_dt is not None else None
    row['days_since_last_used'] = round(days_since_last_used, 2) if days_since_last_used is not None else None
    uses_30d_norm = (row['uses_30d'] / max_30d) if max_30d else 0.0
    uses_7d_norm = (row['uses_7d'] / max_7d) if max_7d else 0.0
    total_uses_norm = (row['total_uses'] / max_total) if max_total else 0.0
    activation_total_norm = (row['activation_total_uses'] / max_activation_total) if max_activation_total else 0.0
    activation_30d_norm = (row['activation_uses_30d'] / max_activation_30d) if max_activation_30d else 0.0
    activation_7d_norm = (row['activation_uses_7d'] / max_activation_7d) if max_activation_7d else 0.0
    recency_score = 0.0 if days_since_last_used is None else clamp01(1.0 - (days_since_last_used / 45.0))
    row['score'] = round(
        weight_30d * uses_30d_norm
        + weight_7d * uses_7d_norm
        + weight_total * total_uses_norm
        + weight_recency * recency_score
        + activation_bonus * activation_total_norm
        + activation_30d_bonus * activation_30d_norm
        + activation_7d_bonus * activation_7d_norm,
        4,
    )

ranked = sorted(
    by_skill.values(),
    key=lambda x: (
        -x['score'],
        -x['activation_uses_30d'],
        -x['activation_uses_7d'],
        -x['activation_total_uses'],
        -x['uses_30d'],
        -x['uses_7d'],
        -x['total_uses'],
        x['days_since_last_used'] if x['days_since_last_used'] is not None else float('inf'),
        x['skill'],
    )
)
result = [{k: v for k, v in row.items() if k != '_last_used_rank'} for row in ranked]
stats.write_text(json.dumps(result, ensure_ascii=False, indent=2))

thresholds = policy.get('thresholds', {}) if isinstance(policy.get('thresholds'), dict) else {}
raw_trailing_percentile = thresholds.get('trailing_percentile', thresholds.get('trailing_percentile_for_repeat_cold', 20))
trailing_percentile = float(raw_trailing_percentile or 20)
if trailing_percentile <= 1:
    percentile_ratio = trailing_percentile
else:
    percentile_ratio = trailing_percentile / 100.0
cut_count = max(1, math.ceil(len(result) * percentile_ratio)) if result else 0
trailing_skills = sorted(
    result,
    key=lambda x: (
        x['score'],
        x['activation_uses_30d'],
        x['activation_uses_7d'],
        x['activation_total_uses'],
        x['uses_30d'],
        x['uses_7d'],
        x['total_uses'],
        -(x['days_since_last_used'] or 0),
        x['skill'],
    ),
)[:cut_count]

activation_nonzero = sum(1 for row in result if row['activation_total_uses'] > 0)
all_activation_sources = Counter()
all_mention_sources = Counter()
for row in result:
    all_activation_sources.update(row['activation_by_source_bucket'])
    all_mention_sources.update(row['mention_by_source_bucket'])

lines = ['# Skill Usage Report', '']
lines.append('## Summary')
lines.append(f'- skills={len(result)}')
lines.append(f'- activation_nonzero_skills={activation_nonzero}')
lines.append(f'- trailing_percentile={trailing_percentile}')
lines.append(f'- trailing_cut_count={cut_count}')
lines.append(f'- activation_source_buckets={dict(all_activation_sources)}')
lines.append(f'- mention_source_buckets={dict(all_mention_sources)}')
lines.append('')
lines.append('## Ranking')
for row in result:
    lines.append(
        f"- {row['skill']}: activations_total={row['activation_total_uses']} activations_30d={row['activation_uses_30d']} activations_7d={row['activation_uses_7d']} activation_by_source_bucket={row['activation_by_source_bucket']} mentions_total={row['total_uses']} mentions_30d={row['uses_30d']} mentions_7d={row['uses_7d']} mention_by_source_bucket={row['mention_by_source_bucket']} last_activated_at={row['last_activated_at']} last_mentioned_at={row['last_mentioned_at']} last_used_at={row['last_used_at']} days_since_last_used={row['days_since_last_used']} score={row['score']}"
    )
lines.append('')
lines.append('## Trailing Percentile Candidates')
for row in trailing_skills:
    lines.append(
        f"- {row['skill']}: activations_total={row['activation_total_uses']} activation_by_source_bucket={row['activation_by_source_bucket']} mentions_total={row['total_uses']} mention_by_source_bucket={row['mention_by_source_bucket']} last_used_at={row['last_used_at']} days_since_last_used={row['days_since_last_used']} score={row['score']}"
    )
report.write_text('\n'.join(lines) + '\n')
print(f'wrote {stats}')
print(f'wrote {report}')
