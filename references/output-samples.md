# 输出样本 / Output Samples

## usage_stats.json 样本

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

## report-latest.md 样本

```markdown
# 技能使用报告 — 2026-04-04

## 最近常用
1. tmux — 最近 7 天使用 12 次
2. codex — 最近 7 天使用 8 次
3. transcendence-memory — 最近 7 天使用 5 次

## 较少使用
- rag-everything-enhancer — 30 天仅使用 2 次
- acpx — 30 天仅使用 1 次

## 归档候选
- acpx（总使用 3 次，近 30 天仅 1 次）

## 受保护（不参与归档判断）
- skill-usage-governor
- long-running-agent
- self-improvement
```

## archive-manifest.json 样本

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
