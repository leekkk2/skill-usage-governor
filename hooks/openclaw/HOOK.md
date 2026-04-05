---
name: skill-usage-governor
description: "Injects skill usage governance reminder during agent bootstrap"
metadata: {"openclaw":{"emoji":"📊","events":["agent:bootstrap"]}}
---

# Skill Usage Governor Hook

Injects a governance reminder during agent bootstrap so the agent actively manages skill usage.

## What It Does

- Fires on `agent:bootstrap`
- Injects a virtual bootstrap note describing how to govern skill usage
- Encourages the agent to:
  - prefer only the necessary skill
  - avoid redundant skill reads
  - notice overused / cold / protected skills
  - treat `skill-usage-governor` as the governance entry when the user asks to enable it

## Enable

Use OpenClaw hook installation / config wiring to enable this hook.
