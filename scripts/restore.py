#!/usr/bin/env python3
import argparse
import json
import shutil
import sys
from pathlib import Path


ARCHIVE_MANIFEST = 'archive-manifest.json'
SNAPSHOT_DIRNAME = 'snapshot'

BASE = Path(__file__).resolve().parents[1]
WORKSPACE = BASE.parents[1]
CONFIG = BASE / 'config' / 'policy.yaml'
SKILLS_DIR = WORKSPACE / 'skills'


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


POLICY = load_policy(CONFIG)
ARCHIVE_ROOT = resolve_archive_root(BASE, POLICY.get('archive', {}).get('root', 'skills_archive'))


def iter_manifest_entries(skill: str):
    if not ARCHIVE_ROOT.exists():
        return []
    matches = []
    for manifest_path in ARCHIVE_ROOT.glob(f'*/{ARCHIVE_MANIFEST}'):
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except Exception:
            continue
        for entry in manifest.get('entries', []):
            if entry.get('skill') != skill:
                continue
            archive_dir = Path(entry.get('archive_path', ''))
            snapshot_dir = Path(entry.get('snapshot_path', '')) if entry.get('snapshot_path') else None
            matches.append({
                'manifest_path': manifest_path,
                'archived_at': entry.get('archived_at') or manifest.get('archived_at') or manifest_path.parent.name,
                'archive_dir': archive_dir,
                'snapshot_dir': snapshot_dir,
            })
    return sorted(matches, key=lambda item: item['archived_at'], reverse=True)


def find_latest_archive(skill: str):
    manifest_matches = iter_manifest_entries(skill)
    if manifest_matches:
        return manifest_matches[0]
    if not ARCHIVE_ROOT.exists():
        return None
    legacy_matches = sorted(
        [p for p in ARCHIVE_ROOT.glob(f'*/{skill}') if p.is_dir() and p.parent.name != SNAPSHOT_DIRNAME],
        key=lambda p: p.parent.name,
        reverse=True,
    )
    if not legacy_matches:
        return None
    return {
        'manifest_path': None,
        'archived_at': legacy_matches[0].parent.name,
        'archive_dir': legacy_matches[0],
        'snapshot_dir': None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skill', required=True)
    parser.add_argument('--dry-run', action='store_true', default=False)
    args = parser.parse_args()

    record = find_latest_archive(args.skill)
    if record is None:
        print(f'archive not found for skill: {args.skill}', file=sys.stderr)
        return 1

    archive_dir = record['archive_dir']
    snapshot_dir = record['snapshot_dir']
    target_dir = SKILLS_DIR / args.skill
    if target_dir.exists():
        print(f'target already exists: {target_dir}', file=sys.stderr)
        return 1
    if not archive_dir.exists():
        print(f'archive path missing: {archive_dir}', file=sys.stderr)
        return 1

    source_dir = snapshot_dir if snapshot_dir and snapshot_dir.exists() else archive_dir
    source_kind = 'snapshot' if source_dir == snapshot_dir else 'archive'

    if args.dry_run:
        print(f'[dry-run] restore {args.skill}')
        print(f'archived_at: {record["archived_at"]}')
        print(f'archive: {archive_dir}')
        print(f'snapshot: {snapshot_dir}')
        print(f'restore_source: {source_dir} ({source_kind})')
        print(f'target: {target_dir}')
        return 0

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    print(f'restored {args.skill}')
    print(f'archived_at: {record["archived_at"]}')
    print(f'archive: {archive_dir}')
    print(f'snapshot: {snapshot_dir}')
    print(f'restore_source: {source_dir} ({source_kind})')
    print(f'target: {target_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
