# skills.sh 安全审计通过指南

> 本文档整理了 skills.sh 平台三大安全审计引擎（Agent Trust Hub、Socket、Snyk）的完整检查项、
> 评判标准与修复指南，供后续开发时遵守以确保审计全部 Pass。
>
> 最后更新：2026-04-09

---

## 目录

1. [审计总览](#1-审计总览)
2. [Agent Trust Hub（Gen）](#2-agent-trust-hubgen)
3. [Socket](#3-socket)
4. [Snyk](#4-snyk)
5. [OWASP Agentic Skills Top 10 (AST10)](#5-owasp-agentic-skills-top-10-ast10)
6. [开发自查清单](#6-开发自查清单)
7. [已知修复记录](#7-已知修复记录)

---

## 1. 审计总览

skills.sh 对每个技能发布时运行三个独立扫描引擎，并在技能详情页展示结果：

| 引擎 | 提供方 | 侧重点 | 结果级别 |
|------|--------|--------|---------|
| Agent Trust Hub | Gen Digital | 内容分析、行为安全、代码执行风险 | Pass / Warn / Fail |
| Socket | Socket.dev | 供应链安全、代码质量、异常模式 | Pass / Warn / Fail |
| Snyk | Snyk | 依赖漏洞、已知 CVE、代码缺陷 | Pass / Warn / Fail |

### 通过条件

- **Pass**：无 CRITICAL/HIGH 发现，风险等级 LOW
- **Warn**：存在 MEDIUM 或多个 LOW 发现
- **Fail**：存在 CRITICAL 或 HIGH 发现，或综合评分低于阈值

### 严重等级定义

| 等级 | 含义 |
|------|------|
| CRITICAL | agent 被劫持或数据外泄 |
| HIGH | 危险操作或凭证暴露 |
| MEDIUM | 信任/质量缺口 |
| LOW | 最佳实践违规 |
| INFO | 观察性提示 |

---

## 2. Agent Trust Hub（Gen）

### 2.1 扫描流水线

Agent Trust Hub 使用多阶段验证流水线：

1. **静态扫描**：模式匹配 + 可选 Semgrep 集成
2. **Hook 检测**：发现并分析安装脚本（post_install.sh 等）
3. **导入链追踪**：构建完整依赖图，追溯代码来源
4. **LLM 审计**：Claude 分析行为不一致（如声称是 formatter 却发起网络请求）
5. **注册表交叉引用**：与 skills.sh 社区数据库比对

### 2.2 风险类别

| 类别 | 标识 | 说明 |
|------|------|------|
| 命令执行 | COMMAND_EXECUTION | subprocess、shell 调用、vm.runInNewContext 等 |
| 远程代码执行 | REMOTE_CODE_EXECUTION | eval、exec、动态加载远程代码 |
| 数据外泄 | DATA_EXFILTRATION | 访问敏感文件、网络外传 |
| Prompt 注入 | PROMPT_INJECTION | SKILL.md 中嵌入操控指令 |
| 上下文投毒 | CONTEXT_POISONING | 嵌入指令改写 agent 身份/权限 |

### 2.3 具体检查项与通过标准

#### 2.3.1 动态代码执行（CRITICAL）

**检查**：是否使用 `eval()`、`exec()`、`vm.runInNewContext()`、`Function()` 或类似机制执行动态代码。

**通过标准**：
- 不使用任何动态代码执行机制
- 配置文件解析使用安全的静态解析器（如 `json.loads`、`yaml.safe_load`）
- 不通过 subprocess 调用解释器执行动态构造的代码字符串

**修复方案**：用纯语言安全解析替代。例如 JSON5 可用正则去注释/尾逗号后 `json.loads`。

#### 2.3.2 硬编码路径与元数据泄露（MEDIUM）

**检查**：源码中是否包含硬编码的绝对路径（如 `/Users/xxx/...`、`/home/xxx/...`），泄露开发者环境信息。

**通过标准**：
- 所有路径使用动态计算：`Path.home()`、`Path(__file__).resolve()`、环境变量
- 配置文件使用模板占位符（如 `{{SKILL_DIR}}`），安装时渲染
- 不暴露任何开发者个人目录结构

#### 2.3.3 Subprocess 命令执行（MEDIUM）

**检查**：是否使用 `subprocess`、`os.system`、`os.popen` 等执行系统命令。

**通过标准**：
- 命令执行必须与技能核心功能直接相关
- 使用列表形式传参（`subprocess.run([...])` 而非 shell 字符串拼接）
- 不使用 `shell=True`
- 命令参数不包含用户可控输入（或已做严格校验）
- 执行的脚本路径由代码动态计算，非硬编码

#### 2.3.4 数据访问边界（MEDIUM）

**检查**：是否访问其他 AI 平台的会话日志、配置文件等敏感数据。

**通过标准**：
- 数据访问范围与技能功能说明一致
- 不访问超出声明范围的文件
- 读取路径使用 `Path.home()` 动态计算
- 不将敏感数据外传到网络

#### 2.3.5 持久化机制（MEDIUM）

**检查**：是否修改其他工具的配置文件实现自动执行。

**通过标准**：
- 持久化行为在文档中明确声明
- 需要用户显式运行启用脚本（如 `enable_governor.py`）
- 不在安装时自动注入 hook
- 提供禁用/卸载方式

#### 2.3.6 输入清洗与 Prompt Injection 防护（MEDIUM）

**检查**：处理外部数据（会话日志、用户输入等）时是否有清洗机制。

**通过标准**：
- 文本片段有长度限制，防止超大输入攻击
- 递归解析有深度限制，防止嵌套攻击
- 不将未清洗的外部文本直接用于决策逻辑
- 使用边界标记区分指令与内容

#### 2.3.7 凭证处理（HIGH）

**检查**：是否硬编码密钥、API Key、密码、连接字符串。

**通过标准**：
- 不在源码中包含任何明文凭证
- 使用环境变量或安全存储
- `.env` 文件在 `.gitignore` 中
- 不在日志或输出中打印凭证

### 2.4 签名与认证机制

通过审计后，Agent Trust Hub 会：

1. 构建所有文件的 SHA-256 Merkle 树
2. 使用 Ed25519 密钥签名根哈希
3. 生成 attestation 与技能一起存储
4. 加载时重新计算 Merkle 根并校验签名（任何文件修改会破坏完整性）

---

## 3. Socket

### 3.1 评分维度

Socket 使用 5 个维度评分（满分 100），综合评分越高越好：

| 维度 | 说明 | 检查内容 |
|------|------|---------|
| Supply Chain | 供应链安全 | 依赖来源、构建可信度、发布者身份 |
| Vulnerability | 已知漏洞 | CVE、已知恶意模式 |
| Quality | 代码质量 | 代码复杂度、可维护性 |
| Maintenance | 维护状态 | 最近更新、发布频率、维护者活跃度 |
| License | 许可合规 | 许可证存在、兼容性 |

### 3.2 告警类型

Socket 支持 60+ 检测类型，5 大类别：

| 类别 | 典型告警 |
|------|---------|
| 供应链风险 | 安装脚本、混淆代码、新创建的发布者账户 |
| 质量问题 | 代码质量低、无测试 |
| 维护问题 | 废弃包、长期未更新 |
| 已知漏洞 | CVE 匹配 |
| 许可问题 | 缺少许可证、不兼容许可 |

### 3.3 异常检测规则（本技能相关）

以下是 Socket 对 agent 技能特别关注的异常模式：

#### 3.3.1 硬编码绝对路径脚本执行（LOW-MEDIUM）

**触发条件**：
- Hook 配置中包含硬编码绝对路径（如 `/Users/xxx/path/to/script.py`）
- 通过 hook 触发本地 Python/Node 脚本执行

**评判因素**：
- Confidence（置信度）：40%-65%
- Severity（严重度）：50%-65%

**通过标准**：
- 使用相对路径或模板占位符
- 不包含指向特定开发者环境的绝对路径
- 脚本路径由安装程序在部署时动态生成

#### 3.3.2 Hook 篡改风险

**触发条件**：
- Event-driven hook 触发代码执行
- 缺少可见的访问控制或完整性校验

**通过标准**：
- Hook 配置文件是模板，安装时渲染
- 被触发的脚本内容可审计
- Hook 不会在非预期事件下触发

#### 3.3.3 供应链依赖风险

**触发条件**：
- 依赖于外部脚本文件（如 `adapter.py`）的完整性
- 无文件完整性校验机制

**通过标准**：
- 关键脚本内容在仓库中可见、可审计
- 安装流程不从外部下载执行未知代码
- 文件路径基于安装位置动态计算

### 3.4 零告警目标

**理想状态**：0 alerts，综合评分接近 1.0

**实际可接受**：仅存在 INFO 级别观察项，无 LOW 及以上告警

---

## 4. Snyk

### 4.1 检查范围

Snyk 主要检查：

| 检查项 | 说明 |
|--------|------|
| 依赖漏洞 | 扫描 package.json、requirements.txt 等依赖文件中的已知 CVE |
| 代码质量 | 代码中的安全缺陷模式 |
| 许可合规 | 依赖的许可证合规性 |
| 配置安全 | 配置文件中的安全问题 |

### 4.2 警告代码

| 代码 | 含义 |
|------|------|
| W007 | 不安全的凭证处理 |
| W011 | 第三方内容暴露（获取不可信内容影响 agent 决策） |
| W012 | 不可验证的外部依赖 |

### 4.3 通过标准

- 无已知 CVE 匹配
- 无 CRITICAL/HIGH 代码缺陷
- 依赖链干净
- 许可证合规

---

## 5. OWASP Agentic Skills Top 10 (AST10)

以下是 OWASP 2026 版 Agentic Skills 十大安全风险，skills.sh 审计参考了这些标准。

### AST01: 恶意技能（CRITICAL）

**风险**：恶意代码直接注入技能注册表。

**预防**：
- 实施 Merkle-root 签名
- 发布和安装时进行自动化行为扫描
- 维护已验证发布者白名单
- 要求 ed25519 代码签名

### AST02: 供应链攻击（CRITICAL）

**风险**：技能构建流水线、仓库或依赖链被污染。

**预防**：
- 发布前强制代码签名
- 实施注册表级透明日志
- 要求 SLSA 框架的来源证明
- 所有嵌套依赖固定到不可变哈希

### AST03: 过度授权（HIGH）

**风险**：技能请求超出功能需要的权限（文件系统、shell、网络）。

**预防**：
- 在技能 schema 中强制最小权限清单
- 为敏感文件创建显式拒绝列表（SOUL.md、MEMORY.md、AGENTS.md）
- 默认拒绝 shell 访问
- 验证所有权限请求是否与功能范围一致

### AST04: 不安全的元数据（HIGH）

**风险**：误导性的技能元数据（仿冒、错误的风险等级标注）。

**预防**：
- 发布时进行静态分析和 manifest lint
- 通过 DID 锚定验证发布者身份
- 标记可疑的相似技能名称

### AST05: 不安全的反序列化（HIGH）

**风险**：YAML/JSON 解析中的代码执行（gadget chain、unsafe tag）。

**预防**：
- 禁用危险 YAML 标签（`!!python/object`、`!!ruby/object`）
- 执行前用严格 JSON Schema 验证配置
- 使用安全解析器：`yaml.safe_load()`、`json.loads()`
- 在受限环境中沙箱化反序列化

### AST06: 弱隔离（HIGH）

**风险**：运行时隔离不足，技能可访问主机文件系统和网络。

**预防**：
- 默认使用 Docker/容器隔离执行技能
- 实施网络分段和 syscall 白名单
- 文件系统访问限制为声明的路径

### AST07: 更新漂移（MEDIUM）

**风险**：未固定版本的技能被静默替换为恶意更新。

**预防**：
- 所有技能版本固定到特定不可变哈希
- 更新前要求显式用户批准
- 使用 lock 文件锁定嵌套依赖

### AST08: 扫描不足（MEDIUM）

**风险**：仅依赖模式匹配的扫描工具，无法检测语义攻击。

**预防**：
- 实施语义 + 行为多工具扫描流水线
- 结合静态分析（AST）、动态分析（沙箱）和行为异常检测

### AST09: 无治理（MEDIUM）

**风险**：缺少技能清单、审批流程、审计日志和身份控制。

**预防**：
- 维护跨平台的技能清单
- 实施审批流程
- 启用结构化审计日志

### AST10: 跨平台复用（MEDIUM）

**风险**：为一个平台设计的技能直接移植到另一个平台，绕过安全审查。

**预防**：
- 采用通用技能格式（Universal Skill Format YAML）
- 每个目标平台要求独立的风险评估
- 每个平台使用独立的签名密钥

---

## 6. 开发自查清单

在提交代码到 skills.sh 之前，逐项检查：

### 代码安全

- [ ] 不使用 `eval()`、`exec()`、`vm.runInNewContext()`、`Function()` 等动态代码执行
- [ ] 不使用 `shell=True` 的 subprocess 调用
- [ ] subprocess 使用列表参数而非字符串拼接
- [ ] 不使用 `yaml.load()`（改用 `yaml.safe_load()`）
- [ ] JSON 解析使用标准 `json.loads()`
- [ ] 不包含硬编码凭证、API Key、密码

### 路径处理

- [ ] 不包含硬编码绝对路径（`/Users/xxx/...`、`/home/xxx/...`）
- [ ] 所有路径使用 `Path.home()`、`Path(__file__).resolve()` 或环境变量动态计算
- [ ] Hook 配置使用模板占位符（`{{SKILL_DIR}}`），安装时渲染
- [ ] 不泄露开发者环境信息

### 输入处理

- [ ] 文本输入有长度限制（防止超大输入）
- [ ] 递归解析有深度限制（防止嵌套攻击）
- [ ] 来自外部的数据经过清洗后才用于决策
- [ ] 命令参数不包含用户可控的未校验输入

### 权限与数据

- [ ] 数据访问范围与技能文档声明一致
- [ ] 不访问超出功能范围的敏感文件
- [ ] 不将敏感数据外传到网络
- [ ] 持久化/hook 注入行为在文档中明确声明
- [ ] 持久化需要用户显式运行启用脚本

### 供应链

- [ ] 不从外部下载并执行未知代码
- [ ] 所有依赖可审计
- [ ] 关键脚本内容在仓库中可见
- [ ] 文件路径基于安装位置动态计算

### 文件与配置

- [ ] `.gitignore` 包含 `.env`、`__pycache__/`、`data/` 等生成产物
- [ ] 不包含编译产物或缓存文件
- [ ] 许可证文件存在且合规

---

## 7. 已知修复记录

### 2026-04-09: 修复 Agent Trust Hub + Socket 双重警告

**问题**：
1. Agent Trust Hub (MEDIUM Warn)：
   - `check_activation.py` 使用 `vm.runInNewContext()` 动态代码执行
   - `collect.py` 硬编码路径 `/Users/zhangweiteng/...`
   - `collect.py` 缺少输入清洗（prompt injection 攻击面）
   - Hook 配置硬编码绝对路径泄露开发环境

2. Socket (3x LOW Warn)：
   - `hooks/claude/hooks.json` 硬编码绝对路径
   - `hooks/gemini/settings.json` 硬编码绝对路径
   - `hooks/windsurf/hooks.json` 硬编码绝对路径

**修复**：
- 移除 `vm.runInNewContext()`，替换为纯 Python JSON5 安全解析
- 硬编码路径替换为 `Path.home()` 动态路径
- 添加 `_sanitize_fragment()` 长度截断 + `_MAX_RECURSION_DEPTH` 递归深度限制
- Hook 配置改用 `{{SKILL_DIR}}` 模板占位符
- `enable_governor.py` 新增 `render_hook_templates()` 安装时渲染

**提交**：`05e5e0e` fix(security): 修复 Agent Trust Hub 和 Socket 安全审计警告

---

## 参考链接

- [skills.sh 安全审计页面](https://skills.sh/audits)
- [Gen Agent Trust Hub 合作公告](https://newsroom.gendigital.com/2026-02-17-Gen-and-Vercel-Partner-to-Bring-Independent-Safety-Verification-to-the-AI-Skills-Ecosystem)
- [Socket 供应链安全博客](https://socket.dev/blog/socket-brings-supply-chain-security-to-skills)
- [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
- [Agent Skill Trust & Signing Service](https://kenhuangus.substack.com/p/agent-skill-trust-and-signing-service)
