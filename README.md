# Skill Usage Governor

[English](README.md) | [中文](README_zh.md)

---

### 🚀 Motivation: Solving "Skill Bloat"
When working with AI Agents, it's common to install a massive amount of skills "just in case." Over time, this leads to:
- **Skill Overload**: Hundreds of installed skills, yet only a handful are regularly used.
- **Decision Noise**: Too many skills increase the noise during tool selection, slowing down the agent and reducing accuracy.
- **Management Chaos**: Difficulty in identifying outdated or redundant skills.

**Skill Usage Governor** is designed to solve these pain points. It acts as a "Skill Janitor," using quantitative data to help you clean up and keep your agent lean and efficient.

### ✨ Key Features
1.  **Automated Usage Tracking**: Injects hooks to record real-time skill usage, supporting weighted statistics across 7-day, 30-day, and total usage.
2.  **Multi-Platform Support**: Native support for Gemini CLI (Codex), Claude Code, Windsurf (Cascade) and Vibe CLI.
3.  **Smart Ranking Reports**: Generates visual reports to instantly identify "Hot Skills" vs. "Cold Skills" that are just gathering dust.
4.  **Safe Soft-Archiving**: Provides a reversible archiving mechanism. Inactive skills are moved to a `skills_archive/` directory instead of being permanently deleted.
5.  **One-Click Restore**: Archived skills can be restored to the active directory at any time.
6.  **Protection Mechanism**: Supports a whitelist to ensure core skills (like the governor itself or task managers) are never archived.

### 🔌 Hook Injection (Cross-Platform Adaptation)
The governor tracks usage by intercepting skill activation events (e.g., `activate_skill`) via hooks:
- **Gemini CLI**: Configure `AfterTool` hook in `~/.gemini/settings.json`.
- **Claude Code**: Configure `PostToolUse` hook in `.claude/hooks.json`.
- **Windsurf (Cascade)**: Configure `post-tool-use` hook in `.windsurf/hooks.json`.
- **Vibe CLI**: Configure `post-tool-call` hook in `vibe.json`.

The project provides a unified adapter layer `hooks/adapter.py` that parses JSON context from different platforms and accurately extracts skill names.

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
