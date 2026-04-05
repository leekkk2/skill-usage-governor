# 测试与验证 / Testing

## 标准验证流程

```bash
# 1. 记录一条测试激活
python3 scripts/record_usage.py --skill skill-usage-governor --source cron

# 2. 采集
python3 scripts/collect.py

# 3. 排名
python3 scripts/rank.py

# 4. 检查输出
cat data/usage_stats.json | python3 -m json.tool
cat data/report-latest.md

# 5. dry-run 归档
python3 scripts/archive.py --dry-run

# 6. 检查启用状态
python3 scripts/check_activation.py
```

## skills-hub 单技能镜像验证

当在 `skills-hub` 镜像内验证本技能时，`skills/` 下可能只有 `skill-usage-governor` 自身。

**单技能镜像的最小通过标准**：

1. `record_usage.py` 能写入一条无副作用的 activation
2. `rank.py` 能在 `usage_stats.json` 中回显该 activation
3. `activation_by_source_bucket` 中能看到预期来源（如 `cron`）

**注意**：不要在单技能镜像中做"全技能统计"验证（会得到假失败）。多技能统计需要完整 skills 工作区或额外准备假技能集。

## 验证夹具

`examples/` 目录包含预制的验证夹具：

| 文件 | 用途 |
|------|------|
| `rule-check.json` | 规则检查输入样本 |
| `rule-check-pass.json` | 预期通过的规则检查 |
| `strict-fail.json` | 严格模式下应失败的样本 |
| `lenient-warn.json` | 宽松模式下应告警的样本 |
