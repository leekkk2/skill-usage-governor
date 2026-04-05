#!/usr/bin/env python3
import argparse
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path


ARCHIVE_MANIFEST = 'archive-manifest.json'
SNAPSHOT_DIRNAME = 'snapshot'


parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true')
parser.add_argument('--live', action='store_true')
args = parser.parse_args()

if args.dry_run and args.live:
    raise SystemExit('cannot use --dry-run and --live together')


def resolve_dry_run(dry_run_flag: bool, live_flag: bool, archive_cfg: dict) -> bool:
    if dry_run_flag:
        return True
    if live_flag:
        return False
    return bool(archive_cfg.get('dry_run_default', False))


def parse_scalar(value: str):
    text = value.strip()
    lowered = text.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def load_policy(path: Path) -> dict:
    if not path.exists():
        raise SystemExit('policy.yaml missing')

    policy = {}
    current_section = None
    with path.open('r', encoding='utf-8') as f:
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
                policy[key.strip()] = parse_scalar(value)
                continue
            if current_section is None:
                continue
            if stripped.startswith('- '):
                if not isinstance(policy[current_section], list):
                    policy[current_section] = []
                policy[current_section].append(parse_scalar(stripped[2:]))
                continue
            if ':' not in stripped:
                continue
            if not isinstance(policy[current_section], dict):
                policy[current_section] = {}
            key, value = stripped.split(':', 1)
            policy[current_section][key.strip()] = parse_scalar(value)

    return policy


def resolve_archive_root(base: Path, root_value) -> Path:
    root = Path(str(root_value or 'skills_archive')).expanduser()
    return root if root.is_absolute() else base / root


BASE = Path(__file__).resolve().parents[1]
WORKSPACE = BASE.parents[1]
SKILLS_DIR = WORKSPACE / 'skills'
DATA = BASE / 'data'
CONFIG = BASE / 'config' / 'policy.yaml'
stats = DATA / 'usage_stats.json'
if not stats.exists():
    raise SystemExit('usage_stats.json missing; run rank.py first')

rows = json.loads(stats.read_text())
policy = load_policy(CONFIG)
protected = set(policy.get('protected_skills', []))
thresholds = policy.get('thresholds', {})
archive_cfg = policy.get('archive', {})
archive_root = resolve_archive_root(BASE, archive_cfg.get('root', 'skills_archive'))
max_total_uses = int(thresholds.get('max_total_uses_for_low_total_rule', 2))
raw_trailing_percentile = thresholds.get('trailing_percentile', thresholds.get('trailing_percentile_for_repeat_cold', 20))
trailing_percentile = float(raw_trailing_percentile or 20)
if trailing_percentile <= 1:
    percentile_ratio = trailing_percentile
else:
    percentile_ratio = trailing_percentile / 100.0
snapshot_before_move = bool(archive_cfg.get('snapshot_before_move', True))
is_dry_run = resolve_dry_run(args.dry_run, args.live, archive_cfg)

filtered_rows = [row for row in rows if row['skill'] not in protected]
trailing_cut_count = max(1, math.ceil(len(filtered_rows) * percentile_ratio)) if filtered_rows else 0
trailing_skills = {
    row['skill']
    for row in sorted(
        filtered_rows,
        key=lambda x: (
            x.get('score', 0),
            x.get('uses_30d', 0),
            x.get('uses_7d', 0),
            x.get('total_uses', 0),
            -(x.get('days_since_last_used') or 0),
            x['skill'],
        ),
    )[:trailing_cut_count]
}

candidates = [
    row for row in filtered_rows
    if row.get('total_uses', 0) <= max_total_uses and row['skill'] in trailing_skills
]
candidates = sorted(
    candidates,
    key=lambda x: (
        x.get('score', 0),
        x.get('uses_30d', 0),
        x.get('uses_7d', 0),
        x.get('total_uses', 0),
        -(x.get('days_since_last_used') or 0),
        x['skill'],
    ),
)

mode_label = 'dry-run' if is_dry_run else 'live'
snapshot_label = 'enabled' if snapshot_before_move else 'disabled'
print(
    f'archive candidates '
    f'(policy-filtered thresholded {mode_label}, total_uses <= {max_total_uses}, snapshot_before_move={snapshot_label}):'
)
for row in candidates:
    trailing_tag = ' trailing-percentile' if row['skill'] in trailing_skills else ''
    print(f"- {row['skill']} (total={row.get('total_uses', 0)}{trailing_tag})")
if is_dry_run:
    print(
        f'trailing percentile context: percentile={trailing_percentile} cut_count={trailing_cut_count} '
        f'matched_candidates={sum(1 for row in candidates if row["skill"] in trailing_skills)}'
    )
    print('dry-run only; no files moved')
    raise SystemExit(0)

if not candidates:
    print('no candidates archived')
    raise SystemExit(0)

timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
archive_batch_dir = archive_root / timestamp
archive_batch_dir.mkdir(parents=True, exist_ok=True)
snapshot_dir = archive_batch_dir / SNAPSHOT_DIRNAME
if snapshot_before_move:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
manifest_rows = []
archived = 0
for row in candidates:
    skill = row['skill']
    src = SKILLS_DIR / skill
    if not src.exists():
        print(f'skip missing skill directory: {src}')
        continue
    dest = archive_batch_dir / skill
    if dest.exists():
        raise SystemExit(f'archive target already exists: {dest}')
    snapshot_path = None
    if snapshot_before_move:
        snapshot_path = snapshot_dir / skill
        if snapshot_path.exists():
            raise SystemExit(f'snapshot target already exists: {snapshot_path}')
        shutil.copytree(src, snapshot_path)
    shutil.move(str(src), str(dest))
    archived += 1
    manifest_rows.append({
        'skill': skill,
        'archived_at': timestamp,
        'archive_path': str(dest),
        'snapshot_path': str(snapshot_path) if snapshot_path else None,
        'score': row.get('score'),
        'total_uses': row.get('total_uses'),
        'activation_total_uses': row.get('activation_total_uses'),
        'days_since_last_used': row.get('days_since_last_used'),
    })
    print(f'archived {skill} -> {dest}')
    if snapshot_path:
        print(f'snapshot {skill} -> {snapshot_path}')

manifest = {
    'archived_at': timestamp,
    'archive_root': str(archive_batch_dir),
    'snapshot_before_move': snapshot_before_move,
    'skills_dir': str(SKILLS_DIR),
    'entries': manifest_rows,
}
(archive_batch_dir / ARCHIVE_MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'archived_count={archived}')
print(f'manifest={archive_batch_dir / ARCHIVE_MANIFEST}')
