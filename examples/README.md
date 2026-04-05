# examples

`examples/` 是 `scripts/check_rules.py` 的正式验证夹具目录。

当前样例职责：

- `rule-check.json`
  - strict 基线失败样例
  - 保留历史兼容名
  - 覆盖：普通 strict 模式下，未读取 `SKILL.md` 会被阻断

- `rule-check-pass.json`
  - strict 成功样例
  - 覆盖：按规则先读后用时可通过检查

- `strict-fail.json`
  - strict + whitelist 失败路径样例
  - 覆盖：受保护/白名单技能应被跳过，但非白名单未读技能仍会被阻断

- `lenient-warn.json`
  - lenient 告警基线样例
  - 当前唯一保留的 lenient 告警夹具
  - 不再保留其他历史 lenient 重复样例
  - 覆盖：未读取 `SKILL.md` 时给 warning，但不阻断

说明：
- 当前目录只保留 4 个正式验证夹具：`rule-check.json`、`rule-check-pass.json`、`strict-fail.json`、`lenient-warn.json`。
- `rule-check.json` 与 `strict-fail.json` 不是重复样例。
- 前者验证“普通 strict 未读阻断”；后者验证“strict + whitelist 下只阻断非白名单技能”。
- 如后续继续裁剪样例，优先保持“每条样例只覆盖一个独立语义”。
- 如新增、替换或删除样例，必须同步更新本文件中的夹具列表与职责说明，避免目录内容与文档口径漂移。
- 如样例职责发生变化，即使文件名不变，也必须同步回写对应条目的职责描述，不允许只改样例内容而不更新说明。
