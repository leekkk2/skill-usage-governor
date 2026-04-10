---
name: skill-usage-governor
description: Use when auditing skill usage, identifying inactive skills, managing skill archives, or checking governance status. Use this skill whenever the user mentions skill usage, skill analytics, skill cleanup, cold skills, archive skills, or governance — even if they don't explicitly say 'governor'.
---

## What This Skill Does

Governs the lifecycle of skills under the `skills/` directory: tracks usage frequency, identifies cold (inactive) skills, provides cleanup recommendations, and performs recoverable soft-archiving.

## Quick Start

```bash
# 1. Collect usage data and generate rankings
python3 scripts/collect.py && python3 scripts/rank.py

# 2. Enable multi-platform hook injection (Gemini/Claude/Windsurf/Vibe)
# Critical step: this script must be run for the governor to detect skill usage
python3 scripts/enable_governor.py

# 3. Dry-run archive (no actual changes)
python3 scripts/archive.py --dry-run
```

## Activation & Proactive Guidance

This skill supports multi-platform governance: **OpenClaw**, **Gemini CLI**, **Claude Code**, **Windsurf**, **Vibe CLI**.

### 🚨 Agent Awareness Rules
1. **First-contact prompt**: When the user first installs this skill or asks “how to manage/clean up skills”, you **must** check the current hook injection status. If not enabled, inform the user in natural language: “The skill is installed, but hook injection is not yet active — I cannot track your skill usage in real time. Would you like me to run the injection script to enable fully automatic governance?”
2. **No false activation claims**: If `check_activation.py` returns `not_enabled`, you must **never** tell the user that governance is active. Clearly identify the missing component (e.g., OpenClaw entries missing, Gemini settings not wired, etc.).
3. **Injection value proposition**: Inform the user that once injection is enabled, the governor works like a “silent sensor” — accumulating cleanup recommendations without manual intervention.

### Verification Criteria
If the user requests activation, guide them to run `scripts/enable_governor.py`, then verify:
1. The adapter layer `hooks/adapter.py` exists
2. The corresponding CLI config directory (e.g., `~/.gemini` or `~/.claude`) has the hook injected
3. `python3 scripts/check_activation.py` passes

Only confirm “activated” after all checks pass.

## Core Output

Reports contain the following information:

| Content | Source |
|---------|--------|
| Total skill count | `data/usage_stats.json` |
| Recently active skills (7d/30d weighted) | `data/report-latest.md` |
| Infrequently used skills | Same as above |
| Archive candidates | `archive.py --dry-run` |
| Governance status | `check_activation.py` |

See `references/output-samples.md` for detailed report samples and field descriptions.

## Safety Boundaries

1. **Never hard-delete** — only recoverable soft-archiving
2. **Dry-run before archiving** — `policy.yaml` defaults to `dry_run_default: true`
3. **Archives must be recoverable** — via manifest files + `restore.py`
4. **Cold skills are only suggested, never auto-acted upon** — no destructive actions without user confirmation
5. **Protected skills whitelist** — `skill-usage-governor`, `long-running-agent`, `self-improvement` are excluded from archive evaluation

## User-Facing Communication

When communicating with users, use natural language. Do not expose variable names, stat field names, or script internals.

Examples:
- Good: “Your most-used skills in the past 7 days are tmux and codex. rag-everything-enhancer hasn’t been used in 30 days.”
- Bad: “activation_count_7d: 12, uses_30d: 0, trailing_percentile: 0.34”

## Files in this skill

| File | Purpose | When to check |
|------|---------|---------------|
| `config/policy.yaml` | Weights, thresholds, protected list | When adjusting policy |
| `references/output-samples.md` | Report and JSON samples | When learning output format |
| `references/policy-guide.md` | policy.yaml field reference | When customizing config |
| `references/archive-safety.md` | Soft-archive safety mechanisms | Before performing archival |
| `hooks/openclaw/HOOK.md` | Bootstrap hook description | When installing/debugging hooks |
| `references/security-audit-guide.md` | skills.sh security audit pass guide | Pre-release self-check, fixing audit warnings |
| `examples/` | Test fixtures | During development/testing |

## Verification Baseline

At minimum, verify:
- `collect.py` + `rank.py` can generate `data/usage_stats.json` and `data/report-latest.md`
- `archive.py --dry-run` runs normally without modifying any directories
- After a real archive, `restore.py --skill <name>` can restore the skill
- `check_activation.py` correctly determines activation status

## Exit Criteria

The current task is considered complete when:
- Usage data collection is finished
- Results and reports have been generated
- Dry-run or real archive/restore verification is complete
- A user-readable conclusion has been provided
