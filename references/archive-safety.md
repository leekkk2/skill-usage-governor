# 软归档安全机制 / Archive Safety

## 设计原则

归档操作遵循"可恢复优先"原则 — 在任何环节出错时，用户都能恢复到归档前的状态。

## 归档流程

```
1. dry-run        → 列出归档候选，不做任何改动
2. 用户确认        → agent 不能跳过确认步骤
3. 移动文件        → skills/<name> → skills_archive/<name>
4. 生成 manifest   → 记录来源路径、时间、恢复命令
5. 恢复            → restore.py --skill <name> 反向操作
```

## 保护层

| 保护层 | 机制 |
|--------|------|
| **受保护白名单** | `policy.yaml` 的 `protected_skills` 列表中的技能永不进入归档候选 |
| **dry-run 默认** | `archive.dry_run_default: true`，即使脚本直接运行也不会真实操作 |
| **用户确认** | agent 必须向用户展示 dry-run 结果并获得确认后才执行 |
| **manifest 记录** | 每次归档生成 JSON manifest，包含完整恢复信息 |
| **可恢复** | `restore.py` 根据 manifest 将技能移回原位 |

## 什么不会发生

- 不会硬删除任何文件
- 不会在用户未确认时执行归档
- 不会归档受保护的技能
- 不会在 dry-run 模式下修改文件系统
- 不会丢失 manifest（manifest 存放在归档目录内）

## 恢复流程

```bash
# 查看已归档的技能
ls skills_archive/

# 恢复指定技能
python3 scripts/restore.py --skill <name>

# 恢复后验证
ls skills/<name>/SKILL.md
```
