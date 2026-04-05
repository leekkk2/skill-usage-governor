# Skill Usage Governor | 技能治理器

[English](#english) | [中文](#中文)

---

## 中文

### 🚀 项目初衷：解决“技能膨胀”
在使用智能体（Agent）的过程中，我们往往会“一股脑”地安装大量技能（Skills）。随着时间的推移，你会发现：
- **技能过载**：安装了上百个技能，但真正经常使用的可能只有那几个。
- **决策干扰**：过多的技能会增加智能体选择工具时的噪声，降低响应速度和准确性。
- **管理混乱**：不知道哪些技能已经过时，哪些是重复的。

**Skill Usage Governor** 正是为了解决这些痛点而生。它像一个“技能管家”，通过量化数据帮你清理门户，让你的智能体始终保持轻盈、高效。

### ✨ 核心功能
1.  **自动统计频率**：通过 Hook 注入，实时记录技能的使用次数，支持 7 天、30 天及总量维度的加权统计。
2.  **智能排名报告**：生成可视化报告，一眼识别哪些是“热门技能”，哪些是常年吃灰的“冷门技能”。
3.  **安全软归档**：提供“可撤销”的归档机制。冷门技能会被移动到 `skills_archive/` 目录，而不是直接删除。
4.  **一键恢复**：归档后的技能如果需要，可以随时一键还原到活跃目录。
5.  **保护机制**：支持白名单配置，确保核心技能（如治理器本身、长程任务管理等）永远不会被归档。

### ⚠️ 重要提醒：显式开启
为了保障安全性与隐私，本治理器**默认不生效**。
用户必须**显式开启**并允许对智能体进行注入。开启流程会验证：
- 技能文件、Hook 脚本、配置文件是否全部接线。
- 运行环境自检是否通过。

> 只有当 `python3 scripts/check_activation.py` 通过后，治理逻辑才正式运行。

### 快速开始
```bash
# 1. 采集并分析使用数据
python3 scripts/collect.py && python3 scripts/rank.py

# 2. 查看最新治理报告
cat data/report-latest.md

# 3. 模拟归档（查看哪些技能将被移动）
python3 scripts/archive.py --dry-run

# 4. 执行恢复
python3 scripts/restore.py --skill <skill-name>
```

---

## English

### 🚀 Motivation: Solving "Skill Bloat"
When working with AI Agents, it's common to install a massive amount of skills "just in case." Over time, this leads to:
- **Skill Overload**: Hundreds of installed skills, yet only a handful are regularly used.
- **Decision Noise**: Too many skills increase the noise during tool selection, slowing down the agent and reducing accuracy.
- **Management Chaos**: Difficulty in identifying outdated or redundant skills.

**Skill Usage Governor** is designed to solve these pain points. It acts as a "Skill Janitor," using quantitative data to help you clean up and keep your agent lean and efficient.

### ✨ Key Features
1.  **Automated Usage Tracking**: Injects hooks to record real-time skill usage, supporting weighted statistics across 7-day, 30-day, and total usage.
2.  **Smart Ranking Reports**: Generates visual reports to instantly identify "Hot Skills" vs. "Cold Skills" that are just gathering dust.
3.  **Safe Soft-Archiving**: Provides a reversible archiving mechanism. Inactive skills are moved to a `skills_archive/` directory instead of being permanently deleted.
4.  **One-Click Restore**: Archived skills can be restored to the active directory at any time.
5.  **Protection Mechanism**: Supports a whitelist to ensure core skills (like the governor itself or task managers) are never archived.

### ⚠️ Important: Explicit Activation
For security and privacy, this governor is **NOT active by default**.
Users must **explicitly enable** it and allow agent injection. The activation process verifies:
- Whether skill files, hook scripts, and config files are properly linked.
- Whether the environment self-check passes.

> Governance logic only runs after `python3 scripts/check_activation.py` passes successfully.

### Quick Start
```bash
# 1. Collect and analyze usage data
python3 scripts/collect.py && python3 scripts/rank.py

# 2. View the latest governance report
cat data/report-latest.md

# 3. Dry-run archive (see which skills will be moved)
python3 scripts/archive.py --dry-run

# 4. Restore a skill
python3 scripts/restore.py --skill <skill-name>
```
