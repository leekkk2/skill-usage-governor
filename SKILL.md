---
name: skill-usage-governor
description: Use when auditing skill usage, identifying inactive skills, managing skill archives, or checking governance status. Use this skill whenever the user mentions skill usage, skill analytics, skill cleanup, cold skills, archive skills, or governance — even if they don't explicitly say 'governor'.
---

## What This Skill Does

治理 `skills/` 目录下的技能生命周期：统计使用频率、识别冷门技能、给出整理建议、执行可恢复的软归档。

## Quick Start

```bash
# 1. 采集使用数据
python3 scripts/collect.py

# 2. 生成排名报告
python3 scripts/rank.py

# 3. 查看报告
cat data/report-latest.md

# 4. 查看归档候选（dry-run，不做任何改动）
python3 scripts/archive.py --dry-run

# 5. 确认后执行真实归档
python3 scripts/archive.py

# 6. 恢复被归档的技能
python3 scripts/restore.py --skill <name>
```

## 启用判断

本技能有两种状态：**未开启** / **已开启**。

如果用户要求"开启"，必须逐项验证（不能假装已开启）：

1. 技能本体存在（`skills/skill-usage-governor/SKILL.md`）
2. Hook 存在（`hooks/openclaw/handler.ts`）
3. 配置已接线（`config/policy.yaml` 可读取）
4. 已重启生效
5. `python3 scripts/check_activation.py` 通过

全部通过后才能回复"已开启"。

## 核心输出

报告包含以下信息：

| 内容 | 来源 |
|------|------|
| 技能总数 | `data/usage_stats.json` |
| 最近常用技能（7d/30d 加权） | `data/report-latest.md` |
| 较少使用的技能 | 同上 |
| 归档候选 | `archive.py --dry-run` |
| 治理状态 | `check_activation.py` |

详细的报告样本和字段说明见 `references/output-samples.md`。

## 安全边界

1. **永不硬删除** — 只做可恢复的软归档
2. **归档前必须 dry-run** — `policy.yaml` 默认 `dry_run_default: true`
3. **归档必须可恢复** — 通过 manifest 文件 + `restore.py`
4. **冷技能只建议，不自动操作** — 无用户确认不做破坏性操作
5. **受保护技能白名单** — `skill-usage-governor`、`long-running-agent`、`self-improvement` 不进入归档判断

## 对外表达

面向用户时使用自然语言，不暴露变量名、统计字段名或脚本细节。

示例：
- 好："最近 7 天你最常用的是 tmux 和 codex，rag-everything-enhancer 已经 30 天没用过了"
- 坏："activation_count_7d: 12, uses_30d: 0, trailing_percentile: 0.34"

## Files in this skill

| 文件 | 用途 | 何时查看 |
|------|------|---------|
| `config/policy.yaml` | 权重、阈值、受保护列表 | 需要调整策略时 |
| `references/output-samples.md` | 报告和 JSON 样本 | 想了解输出格式时 |
| `references/policy-guide.md` | policy.yaml 字段详解 | 需要自定义配置时 |
| `references/archive-safety.md` | 软归档保护机制详解 | 执行归档前 |
| `hooks/openclaw/HOOK.md` | bootstrap hook 说明 | 安装/调试 hook 时 |
| `examples/` | 验证夹具 | 开发/测试时 |

## 验证基线

至少验证：
- `collect.py` + `rank.py` 能生成 `data/usage_stats.json` 和 `data/report-latest.md`
- `archive.py --dry-run` 正常且不改动目录
- 真实归档后 `restore.py --skill <name>` 可恢复
- `check_activation.py` 能正确判断启用状态

## 退出条件

满足以下条件即可视为当前任务完成：
- 已完成使用情况采集
- 已生成结果与报告
- 已完成 dry-run 或真实归档/恢复验证
- 已给出用户可读结论
