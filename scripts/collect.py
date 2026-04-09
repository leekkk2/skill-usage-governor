#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
WORKSPACE = BASE.parents[1]
DATA = BASE / 'data'
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / 'usage_events.jsonl'
TMP_OUT = DATA / 'usage_events.jsonl.tmp'
MERGE_BASELINE = os.environ.get('OPENCLAW_SKILL_USAGE_MERGE_BASELINE', '').strip()
CHECKPOINT_PATH_ENV = os.environ.get('OPENCLAW_SKILL_USAGE_CHECKPOINT_PATH', '').strip()
WRITE_CHECKPOINT_ENV = os.environ.get('OPENCLAW_SKILL_USAGE_WRITE_CHECKPOINT', '1').strip().lower()
DEFAULT_CHECKPOINT = DATA / 'usage_events.checkpoint.json'

DEFAULT_AGENTS_DIR = Path.home() / '.openclaw' / 'agents'
DEFAULT_SESSIONS_DIRS = [DEFAULT_AGENTS_DIR / 'main' / 'sessions']
SESSIONS_DIRS_ENV = os.environ.get('OPENCLAW_SKILL_USAGE_SESSIONS_DIRS')
SESSIONS_DIR_ENV = os.environ.get('OPENCLAW_SKILL_USAGE_SESSIONS_DIR')
SESSION_LIMIT_ENV = os.environ.get('OPENCLAW_SKILL_USAGE_SESSION_LIMIT')
SESSION_SINCE_ENV = os.environ.get('OPENCLAW_SKILL_USAGE_SESSION_SINCE')
SKILLS_DIR = WORKSPACE / 'skills'
IGNORE_PREFIXES = tuple(filter(None, [part.strip() for part in os.environ.get('OPENCLAW_SKILL_USAGE_IGNORE_PREFIXES', 'zz-,tmp-,test-,e2e-').split(',')]))
IGNORE_NAMES = {part.strip() for part in os.environ.get('OPENCLAW_SKILL_USAGE_IGNORE_NAMES', '').split(',') if part.strip()}


def is_ignored_skill_dir(path: Path) -> bool:
    name = path.name
    if name in IGNORE_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in IGNORE_PREFIXES)


SKILL_NAMES = sorted([
    p.name for p in SKILLS_DIR.iterdir()
    if p.is_dir() and (p / 'SKILL.md').exists() and not is_ignored_skill_dir(p)
]) if SKILLS_DIR.exists() else []
SKILL_NAME_SET = set(SKILL_NAMES)
SKILL_TOKEN_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')

PATTERNS = [
    re.compile(r'\bskills/([a-zA-Z0-9._-]+)/SKILL\.md\b'),
    re.compile(r'\b([a-zA-Z0-9._-]+)\b(?=/SKILL\.md)'),
]

ACTIVATION_PATTERNS = {
    'zh_use': lambda skill: re.compile(rf'(?<![\w.-])(使用|用)\s+{re.escape(skill)}(?![\w.-])', re.IGNORECASE),
    'en_use': lambda skill: re.compile(rf'(?<![\w.-])(use|using)\s+{re.escape(skill)}(?![\w.-])', re.IGNORECASE),
    'explicit_name': lambda skill: re.compile(rf'(?<![\w.-]){re.escape(skill)}\s+(技能|skill)(?![\w.-])', re.IGNORECASE),
    'skill_path': lambda skill: re.compile(rf'\bskills/{re.escape(skill)}/SKILL\.md\b', re.IGNORECASE),
}

WORD_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
RUNTIME_SOURCE_BUCKETS = {'cron', 'selfcheck', 'runtime-explicit'}


def has_token_boundary(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else ''
    after = text[end] if end < len(text) else ''
    return before not in WORD_CHARS and after not in WORD_CHARS


def candidate_skills(text: str):
    candidates = set()
    for token in SKILL_TOKEN_RE.findall(text):
        if token in SKILL_NAME_SET:
            candidates.add(token)
    for pat in PATTERNS:
        for m in pat.finditer(text):
            candidate = m.group(1)
            if candidate in SKILL_NAME_SET:
                candidates.add(candidate)
    return candidates


def extract_mentions(text: str):
    found = set()
    lower_text = text.lower()
    candidates = candidate_skills(text)
    for skill in candidates:
        start = 0
        while True:
            idx = text.find(skill, start)
            if idx == -1:
                break
            end = idx + len(skill)
            if has_token_boundary(text, idx, end):
                found.add(skill)
                break
            start = idx + 1
        if skill in found:
            continue
        if skill in text and ('SKILL.md' in text or 'skill' in lower_text or '技能' in text):
            found.add(skill)
    return sorted(found)


def extract_activations(text: str):
    found = set()
    candidates = candidate_skills(text)
    for skill in candidates:
        for factory in ACTIVATION_PATTERNS.values():
            if factory(skill).search(text):
                found.add(skill)
                break
    return sorted(found)


def resolve_session_dirs():
    raw_values = []
    if SESSIONS_DIRS_ENV:
        raw_values.extend(part.strip() for part in SESSIONS_DIRS_ENV.split(os.pathsep))
    elif SESSIONS_DIR_ENV:
        raw_values.append(SESSIONS_DIR_ENV.strip())
    else:
        raw_values.extend(str(path) for path in DEFAULT_SESSIONS_DIRS)
        agents_root = DEFAULT_AGENTS_DIR.expanduser()
        if agents_root.exists():
            raw_values.extend(str(path) for path in sorted(agents_root.glob('*/sessions')))

    resolved = []
    seen = set()
    for raw in raw_values:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if path in seen or not path.exists():
            continue
        seen.add(path)
        resolved.append(path)
    return resolved


SESSIONS_DIRS = resolve_session_dirs()


def resolve_session_limit():
    raw = (SESSION_LIMIT_ENV or '').strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_since_threshold():
    raw = (SESSION_SINCE_ENV or '').strip()
    if not raw:
        return None
    text = raw
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
    return dt.timestamp()


def iter_session_files():
    files = []
    seen = set()
    since_threshold = parse_since_threshold()
    for sessions_dir in SESSIONS_DIRS:
        try:
            candidates = list(sessions_dir.rglob('*.jsonl'))
        except Exception:
            continue
        for path in candidates:
            if '.deleted.' in path.name or '.reset.' in path.name:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            if since_threshold is not None:
                try:
                    if resolved.stat().st_mtime < since_threshold:
                        continue
                except FileNotFoundError:
                    continue
            seen.add(resolved)
            files.append(resolved)
    files = sorted(files)
    limit = resolve_session_limit()
    if limit is not None:
        files = files[-limit:]
    return files


def parse_jsonl(path: Path):
    try:
        with path.open('r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except FileNotFoundError:
        return


def resolve_checkpoint_path() -> Path:
    raw = CHECKPOINT_PATH_ENV or str(DEFAULT_CHECKPOINT)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (BASE / path).resolve()
    return path


def should_write_checkpoint() -> bool:
    return WRITE_CHECKPOINT_ENV not in {'0', 'false', 'no'}


def normalize_event(row: dict):
    if not isinstance(row, dict):
        return None
    if not row.get('skill') or not row.get('event'):
        return None
    normalized = dict(row)
    normalized.setdefault('source_row', 0)
    normalized.setdefault('role', 'unknown')
    normalized.setdefault('origin_bucket', 'unknown')
    normalized.setdefault('session_scope', 'unknown')
    normalized.setdefault('source_bucket', 'unknown')
    return normalized


def load_events_from_jsonl(path: Path):
    loaded = []
    for row in parse_jsonl(path):
        normalized = normalize_event(row)
        if normalized is not None:
            loaded.append(normalized)
    return loaded


def load_events_from_checkpoint(path: Path):
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    items = payload.get('events') if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    loaded = []
    for row in items:
        normalized = normalize_event(row)
        if normalized is not None:
            loaded.append(normalized)
    return loaded


def collect_append_runtime_events(path: Path):
    if not path.exists():
        return []
    runtime_events = []
    for event in load_events_from_jsonl(path):
        if event.get('event') != 'runtime_skill_triggered':
            continue
        source = str(event.get('source') or '')
        if not source.endswith('usage_events.jsonl'):
            continue
        if event.get('source_bucket') not in RUNTIME_SOURCE_BUCKETS:
            continue
        runtime_events.append(event)
    return runtime_events


def load_baseline_events():
    baseline_events = []
    checkpoint_path = resolve_checkpoint_path()

    if MERGE_BASELINE:
        baseline_path = Path(MERGE_BASELINE).expanduser()
        if not baseline_path.is_absolute():
            baseline_path = (BASE / baseline_path).resolve()
        if baseline_path.exists():
            baseline_events.extend(load_events_from_jsonl(baseline_path))
    elif checkpoint_path.exists():
        baseline_events.extend(load_events_from_checkpoint(checkpoint_path))
    elif OUT.exists():
        baseline_events.extend(load_events_from_jsonl(OUT))

    if OUT.exists() and not MERGE_BASELINE:
        baseline_events.extend(collect_append_runtime_events(OUT))

    return baseline_events


def write_checkpoint(events, session_files):
    checkpoint_path = resolve_checkpoint_path()
    payload = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'session_since': SESSION_SINCE_ENV or None,
        'session_limit': resolve_session_limit(),
        'session_files_scanned': len(session_files),
        'events_count': len(events),
        'events': events,
    }
    checkpoint_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return checkpoint_path


_MAX_FRAGMENT_LEN = 50_000  # 单个文本片段最大长度，防止超大输入
_MAX_RECURSION_DEPTH = 10   # 最大递归深度，防止嵌套攻击


def _sanitize_fragment(text: str) -> str:
    """清洗文本片段，截断过长内容"""
    if len(text) > _MAX_FRAGMENT_LEN:
        text = text[:_MAX_FRAGMENT_LEN]
    return text


def iter_text_fragments(node, _depth=0):
    if _depth > _MAX_RECURSION_DEPTH:
        return
    if isinstance(node, str):
        yield _sanitize_fragment(node)
        return
    if isinstance(node, list):
        for item in node:
            yield from iter_text_fragments(item, _depth + 1)
        return
    if isinstance(node, dict):
        for key in ('text', 'content', 'message', 'prompt', 'input', 'output', 'body'):
            if key in node:
                yield from iter_text_fragments(node[key], _depth + 1)


def first_nonblank(*values):
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return None


def row_contains_user_intent(node) -> bool:
    if isinstance(node, str):
        lowered = node.lower()
        return ('use ' in lowered or 'using ' in lowered or '使用' in node or '用' in node)
    if isinstance(node, list):
        return any(row_contains_user_intent(item) for item in node)
    if isinstance(node, dict):
        return any(row_contains_user_intent(value) for value in node.values())
    return False


def classify_origin_bucket(row, role: str) -> str:
    role_value = (role or '').lower()
    if role_value == 'user':
        return 'user'
    if role_value in {'assistant', 'compaction'}:
        return 'assistant'

    message = row.get('message')
    if isinstance(message, dict):
        inner_role = str(message.get('role') or '').lower()
        if inner_role == 'user':
            return 'user'
        if inner_role == 'assistant':
            return 'assistant'
        if inner_role in {'toolcall', 'toolresult'}:
            content = message.get('content')
            if inner_role == 'toolcall':
                return 'assistant'
            if row_contains_user_intent(content):
                return 'user'
            return 'assistant'

    if row.get('type') == 'message' and role_value in {'toolcall', 'toolresult'}:
        return 'assistant'

    return 'unknown'


def classify_session_scope(session_file: Path) -> str:
    text = str(session_file)
    if '/agents/main/sessions/' in text:
        return 'main'
    if '/agents/' in text and '/sessions/' in text:
        return 'agent'
    return 'unknown'


def classify_source_bucket(session_file: Path, row: dict) -> str:
    text = str(session_file)
    source = str(row.get('source') or '').lower()
    role = str(row.get('role') or row.get('type') or '').lower()
    raw = json.dumps(row, ensure_ascii=False).lower()
    if role == 'system' and '[cron:' in raw:
        return 'cron'
    if source.startswith('cron-'):
        return 'cron'
    if 'governor-selfcheck' in source or source == 'runtime-explicit-skill-trigger':
        return 'selfcheck'
    if '/agents/main/sessions/' in text:
        return 'main-session'
    if '/agents/' in text and '/sessions/' in text:
        return 'external-agent'
    return 'unknown'


def emit_events(events, skills, event_type, session_file, row_index, role, ts, origin_bucket, session_scope, source_bucket):
    for skill in skills:
        events.append({
            'skill': skill,
            'event': event_type,
            'source': str(session_file),
            'source_row': row_index,
            'role': role,
            'origin_bucket': origin_bucket,
            'session_scope': session_scope,
            'source_bucket': source_bucket,
            'used_at': ts,
        })


def test_first_nonblank_rejects_nonstrings():
    fallback_now = datetime.now(timezone.utc).isoformat()
    resolved = first_nonblank(123, {'bad': True}, 456, None) or fallback_now
    assert isinstance(resolved, str), 'resolved timestamp should be a string'
    assert 'T' in resolved, 'resolved timestamp should look like ISO-8601'
    assert '+' in resolved or resolved.endswith('Z'), 'resolved timestamp should include timezone information'


if os.environ.get('OPENCLAW_SKILL_USAGE_SELFTEST') == '1':
    test_first_nonblank_rejects_nonstrings()
    print('selftest: ok')
    raise SystemExit(0)


session_files = iter_session_files()
events = load_baseline_events()
for session_file in session_files:
    for row_index, row in enumerate(parse_jsonl(session_file), start=1):
        fragments = list(iter_text_fragments(row))
        search_texts = fragments + [json.dumps(row, ensure_ascii=False)]
        mentions = sorted({skill for text in search_texts for skill in extract_mentions(text)})
        activations = sorted({skill for text in search_texts for skill in extract_activations(text)})
        if not mentions and not activations:
            continue
        ts = first_nonblank(
            row.get('used_at'),
            row.get('timestamp'),
            row.get('ts'),
            row.get('createdAt'),
        ) or datetime.now(timezone.utc).isoformat()
        role = row.get('role') or row.get('type') or 'unknown'
        origin_bucket = classify_origin_bucket(row, role)
        session_scope = classify_session_scope(session_file)
        source_bucket = classify_source_bucket(session_file, row)
        emit_events(events, mentions, 'skill_mentioned', session_file, row_index, role, ts, origin_bucket, session_scope, source_bucket)
        emit_events(events, activations, 'runtime_skill_triggered', session_file, row_index, role, ts, origin_bucket, session_scope, source_bucket)

seen = set()
deduped = []
for event in events:
    key = (
        event['skill'],
        event['source'],
        event.get('source_row'),
        event['role'],
        event.get('origin_bucket'),
        event.get('session_scope'),
        event.get('source_bucket'),
        event['used_at'],
        event['event'],
    )
    if key in seen:
        continue
    seen.add(key)
    deduped.append(event)

with TMP_OUT.open('w', encoding='utf-8') as f:
    for event in deduped:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
TMP_OUT.replace(OUT)

checkpoint_path = None
if should_write_checkpoint():
    checkpoint_path = write_checkpoint(deduped, session_files)

mention_count = sum(1 for e in deduped if e['event'] == 'skill_mentioned')
activation_count = sum(1 for e in deduped if e['event'] == 'runtime_skill_triggered')
print(f'wrote {OUT} (atomic replace via {TMP_OUT.name})')
print(f'merge_baseline={MERGE_BASELINE or "<auto-checkpoint-or-out>"}')
print(f'checkpoint_path={checkpoint_path or "<disabled>"}')
print(f'session_files_scanned={len(session_files)}')
print(f'session_since={SESSION_SINCE_ENV or "<unset>"}')
print(f'events={len(deduped)}')
print(f'mention_events={mention_count}')
print(f'activation_events={activation_count}')
print(f'skills_detected={len(sorted(set(e["skill"] for e in deduped)))}')
