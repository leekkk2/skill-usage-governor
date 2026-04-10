# Testing

## Standard Verification Workflow

```bash
# 1. Record a test activation
python3 scripts/record_usage.py --skill skill-usage-governor --source cron

# 2. Collect
python3 scripts/collect.py

# 3. Rank
python3 scripts/rank.py

# 4. Check output
cat data/usage_stats.json | python3 -m json.tool
cat data/report-latest.md

# 5. Dry-run archive
python3 scripts/archive.py --dry-run

# 6. Check activation status
python3 scripts/check_activation.py
```

## Single-Skill Mirror Verification in skills-hub

When verifying this skill inside a `skills-hub` mirror, only `skill-usage-governor` itself may exist under `skills/`.

**Minimum pass criteria for single-skill mirror**:

1. `record_usage.py` can write a side-effect-free activation entry
2. `rank.py` echoes back that activation in `usage_stats.json`
3. `activation_by_source_bucket` shows the expected source (e.g., `cron`)

**Note**: Do not run "full skill statistics" verification in a single-skill mirror (it will produce false failures). Multi-skill statistics require a complete skills workspace or additional mock skill sets.

## Test Fixtures

The `examples/` directory contains pre-built test fixtures:

| File | Purpose |
|------|---------|
| `rule-check.json` | Rule check input sample |
| `rule-check-pass.json` | Expected-pass rule check |
| `strict-fail.json` | Sample that should fail in strict mode |
| `lenient-warn.json` | Sample that should warn in lenient mode |
