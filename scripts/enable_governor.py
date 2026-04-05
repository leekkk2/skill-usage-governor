#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

# Use dynamic paths instead of hardcoded ones
HOME = Path.home()
# Assuming the skill is in the current working directory or a known subpath
SKILL_DIR = Path(__file__).resolve().parents[1]

def setup_openclaw():
    print("Checking OpenClaw...")
    oc_workspace = HOME / '.openclaw' / 'workspace'
    if not oc_workspace.exists():
        print("OpenClaw workspace not found, skipping.")
        return

    hook_src = SKILL_DIR / 'hooks' / 'openclaw'
    hook_dst = HOME / '.openclaw' / 'hooks' / 'skill-usage-governor'
    config_path = HOME / '.openclaw' / 'openclaw.json'

    if not config_path.exists():
        print(f"OpenClaw config not found at {config_path}")
        return

    hook_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hook_src / 'HOOK.md', hook_dst / 'HOOK.md')
    shutil.copy2(hook_src / 'handler.ts', hook_dst / 'handler.ts')

    # Note: Complex JSON5-like parsing removed for brevity in this generic version
    # Real implementation should handle the JSON update carefully
    print(f"OpenClaw hook files copied to {hook_dst}. Please ensure hooks are enabled in {config_path}")

def setup_gemini():
    print("Checking Gemini CLI (Codex)...")
    gemini_dir = HOME / '.gemini'
    if not gemini_dir.exists():
        gemini_dir.mkdir(parents=True, exist_ok=True)
    
    settings_path = gemini_dir / 'settings.json'
    hook_config = SKILL_DIR / 'hooks' / 'gemini' / 'settings.json'
    
    print(f"Gemini settings can be found at {settings_path}")
    print(f"Recommended hook config is in {hook_config}")
    # Suggest manual merge or implement auto-merge if safe

def setup_claude():
    print("Checking Claude Code...")
    claude_dir = HOME / '.claude'
    if not claude_dir.exists():
        print("Claude config directory not found, skipping.")
        return
    
    # Claude hooks are often per-project, providing a global reference
    print(f"Claude Code hooks template available at {SKILL_DIR / 'hooks' / 'claude' / 'hooks.json'}")

def setup_vibe_coding_clis():
    print("Checking other Vibe Coding CLIs...")
    # Add logic for Windsurf, Vibe, etc.
    platforms = {
        "Windsurf": HOME / ".windsurf",
        "Vibe": HOME / ".vibe"
    }
    for name, path in platforms.items():
        if path.exists():
            print(f"Found {name} at {path}")
        else:
            print(f"{name} not detected.")

def main() -> int:
    print(f"--- Skill Usage Governor Activation ---")
    print(f"Skill Path: {SKILL_DIR}")
    
    setup_openclaw()
    setup_gemini()
    setup_claude()
    setup_vibe_coding_clis()
    
    # Run self-check
    check_script = SKILL_DIR / 'scripts' / 'check_activation.py'
    if check_script.exists():
        print("\nRunning activation self-check...")
        try:
            subprocess.run(['python3', str(check_script)], check=True)
        except subprocess.CalledProcessError:
            print("Self-check failed. Please check the logs.")
    
    print("\nActivation process completed.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
