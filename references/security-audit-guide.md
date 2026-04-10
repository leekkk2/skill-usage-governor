# skills.sh Security Audit Pass Guide

> This document compiles the complete checklist, evaluation criteria, and remediation guide
> for the three security audit engines on the skills.sh platform (Agent Trust Hub, Socket, Snyk),
> to ensure all audits pass during future development.
>
> Last updated: 2026-04-09

---

## Table of Contents

1. [Audit Overview](#1-audit-overview)
2. [Agent Trust Hub (Gen)](#2-agent-trust-hubgen)
3. [Socket](#3-socket)
4. [Snyk](#4-snyk)
5. [OWASP Agentic Skills Top 10 (AST10)](#5-owasp-agentic-skills-top-10-ast10)
6. [Developer Self-Check Checklist](#6-developer-self-check-checklist)
7. [Known Fix Records](#7-known-fix-records)

---

## 1. Audit Overview

skills.sh runs three independent scanning engines on each skill at publish time and displays results on the skill detail page:

| Engine | Provider | Focus | Result Levels |
|--------|----------|-------|---------------|
| Agent Trust Hub | Gen Digital | Content analysis, behavioral safety, code execution risk | Pass / Warn / Fail |
| Socket | Socket.dev | Supply chain security, code quality, anomaly patterns | Pass / Warn / Fail |
| Snyk | Snyk | Dependency vulnerabilities, known CVEs, code defects | Pass / Warn / Fail |

### Pass Conditions

- **Pass**: No CRITICAL/HIGH findings, risk level LOW
- **Warn**: MEDIUM findings or multiple LOW findings present
- **Fail**: CRITICAL or HIGH findings present, or composite score below threshold

### Severity Definitions

| Level | Meaning |
|-------|---------|
| CRITICAL | Agent hijacking or data exfiltration |
| HIGH | Dangerous operations or credential exposure |
| MEDIUM | Trust/quality gaps |
| LOW | Best practice violations |
| INFO | Observational notes |

---

## 2. Agent Trust Hub (Gen)

### 2.1 Scanning Pipeline

Agent Trust Hub uses a multi-stage verification pipeline:

1. **Static scan**: Pattern matching + optional Semgrep integration
2. **Hook detection**: Discovers and analyzes install scripts (post_install.sh, etc.)
3. **Import chain tracing**: Builds a complete dependency graph, traces code origins
4. **LLM audit**: Claude analyzes behavioral inconsistencies (e.g., a skill claiming to be a formatter but making network requests)
5. **Registry cross-reference**: Compares against the skills.sh community database

### 2.2 Risk Categories

| Category | Identifier | Description |
|----------|-----------|-------------|
| Command Execution | COMMAND_EXECUTION | subprocess, shell calls, vm.runInNewContext, etc. |
| Remote Code Execution | REMOTE_CODE_EXECUTION | eval, exec, dynamic loading of remote code |
| Data Exfiltration | DATA_EXFILTRATION | Accessing sensitive files, network exfiltration |
| Prompt Injection | PROMPT_INJECTION | Manipulative instructions embedded in SKILL.md |
| Context Poisoning | CONTEXT_POISONING | Embedded instructions that alter agent identity/permissions |

### 2.3 Specific Checks and Pass Criteria

#### 2.3.1 Dynamic Code Execution (CRITICAL)

**Check**: Whether `eval()`, `exec()`, `vm.runInNewContext()`, `Function()`, or similar mechanisms are used for dynamic code execution.

**Pass criteria**:
- No dynamic code execution mechanisms used
- Config file parsing uses safe static parsers (e.g., `json.loads`, `yaml.safe_load`)
- No dynamically constructed code strings executed via subprocess interpreters

**Remediation**: Replace with safe language-native parsing. For example, JSON5 can be handled by stripping comments/trailing commas with regex, then using `json.loads`.

#### 2.3.2 Hardcoded Paths and Metadata Leakage (MEDIUM)

**Check**: Whether source code contains hardcoded absolute paths (e.g., `/Users/xxx/...`, `/home/xxx/...`) that leak developer environment information.

**Pass criteria**:
- All paths computed dynamically: `Path.home()`, `Path(__file__).resolve()`, environment variables
- Config files use template placeholders (e.g., `{{SKILL_DIR}}`), rendered at install time
- No developer-specific directory structures exposed

#### 2.3.3 Subprocess Command Execution (MEDIUM)

**Check**: Whether `subprocess`, `os.system`, `os.popen`, etc. are used to execute system commands.

**Pass criteria**:
- Command execution is directly related to core skill functionality
- Arguments passed as lists (`subprocess.run([...])` instead of shell string concatenation)
- `shell=True` not used
- Command arguments do not contain user-controllable input (or are strictly validated)
- Script paths computed dynamically by code, not hardcoded

#### 2.3.4 Data Access Boundaries (MEDIUM)

**Check**: Whether the skill accesses session logs, config files, or other sensitive data from other AI platforms.

**Pass criteria**:
- Data access scope matches the skill's functional description
- No files accessed beyond the declared scope
- Read paths computed dynamically using `Path.home()`
- Sensitive data not transmitted over the network

#### 2.3.5 Persistence Mechanisms (MEDIUM)

**Check**: Whether the skill modifies other tools' config files to achieve auto-execution.

**Pass criteria**:
- Persistence behavior explicitly declared in documentation
- User must explicitly run an enablement script (e.g., `enable_governor.py`)
- Hooks not auto-injected at install time
- Disable/uninstall mechanism provided

#### 2.3.6 Input Sanitization and Prompt Injection Protection (MEDIUM)

**Check**: Whether sanitization mechanisms exist when processing external data (session logs, user input, etc.).

**Pass criteria**:
- Text fragments have length limits to prevent oversized input attacks
- Recursive parsing has depth limits to prevent nesting attacks
- Unsanitized external text is not directly used in decision logic
- Boundary markers separate instructions from content

#### 2.3.7 Credential Handling (HIGH)

**Check**: Whether secrets, API keys, passwords, or connection strings are hardcoded.

**Pass criteria**:
- No plaintext credentials in source code
- Environment variables or secure storage used
- `.env` files listed in `.gitignore`
- Credentials not printed in logs or output

### 2.4 Signing and Attestation Mechanism

After passing audit, Agent Trust Hub will:

1. Build a SHA-256 Merkle tree of all files
2. Sign the root hash with an Ed25519 key
3. Generate an attestation stored alongside the skill
4. Recompute the Merkle root and verify the signature on load (any file modification breaks integrity)

---

## 3. Socket

### 3.1 Scoring Dimensions

Socket uses 5 scoring dimensions (max 100 each); higher composite score is better:

| Dimension | Description | Checks |
|-----------|-------------|--------|
| Supply Chain | Supply chain security | Dependency sources, build trustworthiness, publisher identity |
| Vulnerability | Known vulnerabilities | CVEs, known malicious patterns |
| Quality | Code quality | Code complexity, maintainability |
| Maintenance | Maintenance status | Recent updates, release frequency, maintainer activity |
| License | License compliance | License presence, compatibility |

### 3.2 Alert Types

Socket supports 60+ detection types across 5 major categories:

| Category | Typical Alerts |
|----------|---------------|
| Supply chain risks | Install scripts, obfuscated code, newly created publisher accounts |
| Quality issues | Low code quality, no tests |
| Maintenance issues | Abandoned packages, long-term inactivity |
| Known vulnerabilities | CVE matches |
| License issues | Missing license, incompatible licenses |

### 3.3 Anomaly Detection Rules (Relevant to This Skill)

The following are anomaly patterns Socket specifically watches for in agent skills:

#### 3.3.1 Hardcoded Absolute Path Script Execution (LOW-MEDIUM)

**Trigger conditions**:
- Hook config contains hardcoded absolute paths (e.g., `/Users/xxx/path/to/script.py`)
- Local Python/Node scripts triggered via hooks

**Evaluation factors**:
- Confidence: 40%-65%
- Severity: 50%-65%

**Pass criteria**:
- Use relative paths or template placeholders
- No absolute paths pointing to specific developer environments
- Script paths dynamically generated by the installer at deployment time

#### 3.3.2 Hook Tampering Risk

**Trigger conditions**:
- Event-driven hooks triggering code execution
- Lack of visible access control or integrity verification

**Pass criteria**:
- Hook config files are templates, rendered at install time
- Triggered script contents are auditable
- Hooks do not fire on unexpected events

#### 3.3.3 Supply Chain Dependency Risk

**Trigger conditions**:
- Dependency on external script file integrity (e.g., `adapter.py`)
- No file integrity verification mechanism

**Pass criteria**:
- Critical script contents visible and auditable in the repository
- Install process does not download and execute unknown code from external sources
- File paths computed dynamically based on install location

### 3.4 Zero-Alert Target

**Ideal state**: 0 alerts, composite score approaching 1.0

**Acceptable**: Only INFO-level observations, no LOW or above alerts

---

## 4. Snyk

### 4.1 Scan Scope

Snyk primarily checks:

| Check | Description |
|-------|-------------|
| Dependency vulnerabilities | Scans dependency files (package.json, requirements.txt, etc.) for known CVEs |
| Code quality | Security defect patterns in code |
| License compliance | Dependency license compliance |
| Configuration security | Security issues in config files |

### 4.2 Warning Codes

| Code | Meaning |
|------|---------|
| W007 | Insecure credential handling |
| W011 | Third-party content exposure (fetching untrusted content that influences agent decisions) |
| W012 | Unverifiable external dependencies |

### 4.3 Pass Criteria

- No known CVE matches
- No CRITICAL/HIGH code defects
- Clean dependency chain
- License compliant

---

## 5. OWASP Agentic Skills Top 10 (AST10)

The following is the OWASP 2026 edition of Agentic Skills top 10 security risks, referenced by skills.sh audits.

### AST01: Malicious Skills (CRITICAL)

**Risk**: Malicious code directly injected into the skill registry.

**Prevention**:
- Implement Merkle-root signing
- Perform automated behavioral scanning at publish and install time
- Maintain a verified publisher whitelist
- Require ed25519 code signing

### AST02: Supply Chain Attacks (CRITICAL)

**Risk**: Skill build pipelines, repositories, or dependency chains compromised.

**Prevention**:
- Enforce code signing before publishing
- Implement registry-level transparency logs
- Require SLSA framework provenance attestations
- Pin all nested dependencies to immutable hashes

### AST03: Over-Permissioning (HIGH)

**Risk**: Skills requesting permissions beyond functional needs (file system, shell, network).

**Prevention**:
- Enforce minimum privilege manifests in skill schemas
- Create explicit deny lists for sensitive files (SOUL.md, MEMORY.md, AGENTS.md)
- Default-deny shell access
- Verify all permission requests align with functional scope

### AST04: Insecure Metadata (HIGH)

**Risk**: Misleading skill metadata (impersonation, incorrect risk level labels).

**Prevention**:
- Perform static analysis and manifest linting at publish time
- Verify publisher identity via DID anchoring
- Flag suspiciously similar skill names

### AST05: Insecure Deserialization (HIGH)

**Risk**: Code execution in YAML/JSON parsing (gadget chains, unsafe tags).

**Prevention**:
- Disable dangerous YAML tags (`!!python/object`, `!!ruby/object`)
- Validate config with strict JSON Schema before execution
- Use safe parsers: `yaml.safe_load()`, `json.loads()`
- Sandbox deserialization in restricted environments

### AST06: Weak Isolation (HIGH)

**Risk**: Insufficient runtime isolation; skills can access host file system and network.

**Prevention**:
- Default to Docker/container isolation for skill execution
- Implement network segmentation and syscall whitelists
- Restrict file system access to declared paths

### AST07: Update Drift (MEDIUM)

**Risk**: Unpinned skill versions silently replaced with malicious updates.

**Prevention**:
- Pin all skill versions to specific immutable hashes
- Require explicit user approval before updates
- Use lock files to pin nested dependencies

### AST08: Insufficient Scanning (MEDIUM)

**Risk**: Relying solely on pattern-matching scanning tools that cannot detect semantic attacks.

**Prevention**:
- Implement semantic + behavioral multi-tool scanning pipelines
- Combine static analysis (AST), dynamic analysis (sandbox), and behavioral anomaly detection

### AST09: No Governance (MEDIUM)

**Risk**: Missing skill inventory, approval workflows, audit logs, and identity controls.

**Prevention**:
- Maintain cross-platform skill inventories
- Implement approval workflows
- Enable structured audit logs

### AST10: Cross-Platform Reuse (MEDIUM)

**Risk**: Skills designed for one platform directly ported to another, bypassing security review.

**Prevention**:
- Adopt Universal Skill Format YAML
- Require independent risk assessments for each target platform
- Use separate signing keys per platform

---

## 6. Developer Self-Check Checklist

Check each item before submitting code to skills.sh:

### Code Security

- [ ] No use of `eval()`, `exec()`, `vm.runInNewContext()`, `Function()`, or other dynamic code execution
- [ ] No `shell=True` subprocess calls
- [ ] Subprocess uses list arguments, not string concatenation
- [ ] No use of `yaml.load()` (use `yaml.safe_load()` instead)
- [ ] JSON parsing uses standard `json.loads()`
- [ ] No hardcoded credentials, API keys, or passwords

### Path Handling

- [ ] No hardcoded absolute paths (`/Users/xxx/...`, `/home/xxx/...`)
- [ ] All paths computed dynamically using `Path.home()`, `Path(__file__).resolve()`, or environment variables
- [ ] Hook configs use template placeholders (`{{SKILL_DIR}}`), rendered at install time
- [ ] No developer environment information leaked

### Input Handling

- [ ] Text input has length limits (prevents oversized input)
- [ ] Recursive parsing has depth limits (prevents nesting attacks)
- [ ] External data is sanitized before use in decision logic
- [ ] Command arguments do not contain unvalidated user-controllable input

### Permissions and Data

- [ ] Data access scope matches the skill's documented functionality
- [ ] No access to sensitive files beyond functional scope
- [ ] Sensitive data not transmitted over the network
- [ ] Persistence/hook injection behavior explicitly declared in documentation
- [ ] Persistence requires user to explicitly run an enablement script

### Supply Chain

- [ ] No downloading and executing unknown code from external sources
- [ ] All dependencies are auditable
- [ ] Critical script contents visible in the repository
- [ ] File paths computed dynamically based on install location

### Files and Configuration

- [ ] `.gitignore` includes `.env`, `__pycache__/`, `data/`, and other generated artifacts
- [ ] No compiled artifacts or cache files included
- [ ] License file exists and is compliant

---

## 7. Known Fix Records

### 2026-04-09: Fixed Agent Trust Hub + Socket Dual Warnings

**Issues**:
1. Agent Trust Hub (MEDIUM Warn):
   - `check_activation.py` used `vm.runInNewContext()` dynamic code execution
   - `collect.py` hardcoded path `/Users/zhangweiteng/...`
   - `collect.py` lacked input sanitization (prompt injection attack surface)
   - Hook configs hardcoded absolute paths, leaking dev environment

2. Socket (3x LOW Warn):
   - `hooks/claude/hooks.json` hardcoded absolute path
   - `hooks/gemini/settings.json` hardcoded absolute path
   - `hooks/windsurf/hooks.json` hardcoded absolute path

**Fixes**:
- Removed `vm.runInNewContext()`, replaced with pure Python JSON5 safe parsing
- Hardcoded paths replaced with `Path.home()` dynamic paths
- Added `_sanitize_fragment()` length truncation + `_MAX_RECURSION_DEPTH` recursion depth limit
- Hook configs switched to `{{SKILL_DIR}}` template placeholders
- `enable_governor.py` added `render_hook_templates()` for install-time rendering

**Commit**: `05e5e0e` fix(security): fix Agent Trust Hub and Socket security audit warnings

---

## References

- [skills.sh Security Audit Page](https://skills.sh/audits)
- [Gen Agent Trust Hub Partnership Announcement](https://newsroom.gendigital.com/2026-02-17-Gen-and-Vercel-Partner-to-Bring-Independent-Safety-Verification-to-the-AI-Skills-Ecosystem)
- [Socket Supply Chain Security Blog](https://socket.dev/blog/socket-brings-supply-chain-security-to-skills)
- [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
- [Agent Skill Trust & Signing Service](https://kenhuangus.substack.com/p/agent-skill-trust-and-signing-service)
