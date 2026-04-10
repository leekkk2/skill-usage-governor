# Policy Guide

`config/policy.yaml` controls governance behavior.

## Field Reference

### protected_skills

List of skills excluded from archive evaluation. These will never appear as archive candidates, even with zero usage.

```yaml
protected_skills:
  - skill-usage-governor   # The governance tool itself
  - long-running-agent     # Long-running task framework
  - self-improvement       # Self-improvement
```

### thresholds

Criteria for determining "low activity" status.

```yaml
thresholds:
  trailing_percentile: 0.34    # Skills in the bottom 34% are considered low activity
  max_total_uses_for_low_total_rule: 1  # Skills with total uses ≤ 1 are directly marked as low activity
```

### weights

Ranking formula: `score = uses_7d × 3 + uses_30d × 2 + total_uses × 1`

```yaml
weights:
  uses_7d: 3      # Highest weight for past 7 days (recency)
  uses_30d: 2     # Second weight for past 30 days
  total_uses: 1   # Lowest weight for historical total
```

### activation_weights

Bonus points for activation events (as opposed to mere mentions).

```yaml
activation_weights:
  activation_bonus: 5        # +5 points for any activation record
  activation_30d_bonus: 3    # +3 extra points for activation within 30 days
  activation_7d_bonus: 2     # +2 extra points for activation within 7 days
```

### archive

Archive behavior configuration.

```yaml
archive:
  root: skills_archive      # Archive directory name
  dry_run_default: true      # Default to dry-run (no actual changes)
```

## Customization Examples

To more aggressively clean up cold skills:

```yaml
thresholds:
  trailing_percentile: 0.5        # Bottom 50% considered low activity
  max_total_uses_for_low_total_rule: 3  # Total uses ≤ 3 marked as low activity
```

To protect additional skills:

```yaml
protected_skills:
  - skill-usage-governor
  - long-running-agent
  - self-improvement
  - transcendence-memory     # Newly protected
```
