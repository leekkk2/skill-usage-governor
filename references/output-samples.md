# Output Samples

## usage_stats.json Sample

```json
{
  "generated_at": "2026-04-04T12:00:00Z",
  "total_skills": 7,
  "skills": [
    {
      "name": "tmux",
      "uses_7d": 12,
      "uses_30d": 45,
      "total_uses": 203,
      "weighted_score": 89.5,
      "rank": 1,
      "status": "active"
    },
    {
      "name": "codex",
      "uses_7d": 8,
      "uses_30d": 30,
      "total_uses": 150,
      "weighted_score": 64.0,
      "rank": 2,
      "status": "active"
    },
    {
      "name": "rag-everything-enhancer",
      "uses_7d": 0,
      "uses_30d": 2,
      "total_uses": 15,
      "weighted_score": 4.0,
      "rank": 6,
      "status": "low_activity"
    }
  ]
}
```

## report-latest.md Sample

```markdown
# Skill Usage Report — 2026-04-04

## Recently Active
1. tmux — 12 uses in the past 7 days
2. codex — 8 uses in the past 7 days
3. transcendence-memory — 5 uses in the past 7 days

## Infrequently Used
- rag-everything-enhancer — only 2 uses in 30 days
- acpx — only 1 use in 30 days

## Archive Candidates
- acpx (3 total uses, only 1 in the past 30 days)

## Protected (excluded from archive evaluation)
- skill-usage-governor
- long-running-agent
- self-improvement
```

## archive-manifest.json Sample

```json
{
  "archived_at": "2026-04-04T12:30:00Z",
  "skill": "acpx",
  "source_path": "skills/acpx",
  "archive_path": "skills_archive/acpx",
  "manifest_version": 1,
  "restore_command": "python3 scripts/restore.py --skill acpx"
}
```
