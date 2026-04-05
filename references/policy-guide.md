# Policy 配置指南 / Policy Guide

`config/policy.yaml` 控制治理行为。

## 字段说明

### protected_skills

不参与归档判断的技能列表。即使使用频率为零也不会出现在归档候选中。

```yaml
protected_skills:
  - skill-usage-governor   # 治理工具自身
  - long-running-agent     # 长期任务框架
  - self-improvement       # 自我改进
```

### thresholds

决定"低活跃"判断标准。

```yaml
thresholds:
  trailing_percentile: 0.34    # 排名在后 34% 的技能视为低活跃
  max_total_uses_for_low_total_rule: 1  # 总使用 ≤ 1 次直接标记为低活跃
```

### weights

排名的加权公式：`score = uses_7d × 3 + uses_30d × 2 + total_uses × 1`

```yaml
weights:
  uses_7d: 3      # 近 7 天权重最高（时效性）
  uses_30d: 2     # 近 30 天次之
  total_uses: 1   # 历史总量权重最低
```

### activation_weights

激活事件（区别于"提及"）的加分。

```yaml
activation_weights:
  activation_bonus: 5        # 有激活记录的技能加 5 分
  activation_30d_bonus: 3    # 30 天内有激活额外加 3 分
  activation_7d_bonus: 2     # 7 天内有激活额外加 2 分
```

### archive

归档行为配置。

```yaml
archive:
  root: skills_archive      # 归档目录名
  dry_run_default: true      # 默认 dry-run（不做实际改动）
```

## 自定义示例

如果想更激进地清理冷门技能：

```yaml
thresholds:
  trailing_percentile: 0.5        # 后 50% 都视为低活跃
  max_total_uses_for_low_total_rule: 3  # 总使用 ≤ 3 次标记
```

如果想保护更多技能：

```yaml
protected_skills:
  - skill-usage-governor
  - long-running-agent
  - self-improvement
  - transcendence-memory     # 新增保护
```
