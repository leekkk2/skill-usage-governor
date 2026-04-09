#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

HOME = Path.home()
# The current directory is where the source code lives
SOURCE_DIR = Path(__file__).resolve().parents[1]

def sync_skill_to_workspace():
    workspace_skill_dir = HOME / '.openclaw' / 'workspace' / 'skills' / 'skill-usage-governor'
    print(f"Syncing skill files to {workspace_skill_dir}...")

    if workspace_skill_dir.exists():
        shutil.rmtree(workspace_skill_dir)

    # Copy essential files/dirs
    workspace_skill_dir.mkdir(parents=True, exist_ok=True)

    # We only need SKILL.md and hooks for activation check,
    # but let's copy everything to make it a functional skill in the workspace.
    for item in SOURCE_DIR.iterdir():
        if item.name.startswith('.'): continue
        if item.is_dir():
            shutil.copytree(item, workspace_skill_dir / item.name)
        else:
            shutil.copy2(item, workspace_skill_dir / item.name)

    return workspace_skill_dir

def update_openclaw_config(workspace_skill_dir: Path):
    config_path = HOME / '.openclaw' / 'openclaw.json'
    if not config_path.exists():
        print(f"OpenClaw config not found at {config_path}")
        return False

    print(f"Updating OpenClaw config at {config_path}...")
    try:
        # Using node to read JSON5-ish config if possible, but dumping back as standard JSON is fine
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"Failed to read config: {e}")
        return False

    # 1. Enable internal hook entries
    hooks = cfg.setdefault('hooks', {})
    internal = hooks.setdefault('internal', {})
    internal['enabled'] = True
    entries = internal.setdefault('entries', {})
    entries['skill-usage-governor'] = {"enabled": True}

    # 2. Add install record
    installs = internal.setdefault('installs', {})
    hook_dst = HOME / '.openclaw' / 'hooks' / 'skill-usage-governor'
    installs['skill-usage-governor'] = {
        "source": "path",
        "sourcePath": str(workspace_skill_dir / 'hooks' / 'openclaw'),
        "installPath": str(hook_dst),
        "installedAt": "2026-04-05T12:00:00+08:00",
        "hooks": ["skill-usage-governor"]
    }

    # 3. Add to main agent skills
    agents = cfg.setdefault('agents', {})
    agent_list = agents.setdefault('list', [])
    main_agent = next((a for a in agent_list if a.get('id') == 'main'), None)
    if not main_agent:
        main_agent = {"id": "main"}
        agent_list.append(main_agent)

    agent_skills = main_agent.setdefault('skills', [])
    if 'skill-usage-governor' not in agent_skills:
        agent_skills.append('skill-usage-governor')

    # 4. Save config
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("Config updated successfully.")
    except Exception as e:
        print(f"Failed to write config: {e}")
        return False

    return True

def setup_runtime_hooks():
    hook_src = SOURCE_DIR / 'hooks' / 'openclaw'
    hook_dst = HOME / '.openclaw' / 'hooks' / 'skill-usage-governor'

    print(f"Ensuring runtime hooks in {hook_dst}...")
    hook_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hook_src / 'HOOK.md', hook_dst / 'HOOK.md')
    shutil.copy2(hook_src / 'handler.ts', hook_dst / 'handler.ts')

def render_hook_templates(skill_dir: Path):
    """将 hook 模板中的 {{SKILL_DIR}} 占位符替换为实际技能安装路径"""
    template_dirs = ['claude', 'gemini', 'windsurf', 'vibe']
    template_files = {
        'claude': 'hooks.json',
        'gemini': 'settings.json',
        'windsurf': 'hooks.json',
        'vibe': 'vibe.json',
    }
    for platform in template_dirs:
        template_file = skill_dir / 'hooks' / platform / template_files[platform]
        if not template_file.exists():
            continue
        content = template_file.read_text(encoding='utf-8')
        if '{{SKILL_DIR}}' in content:
            rendered = content.replace('{{SKILL_DIR}}', str(skill_dir))
            template_file.write_text(rendered, encoding='utf-8')
            print(f"  渲染 hook 模板: {template_file}")


def main() -> int:
    print(f"--- Skill Usage Governor Activation (OpenClaw) ---")

    workspace_skill_dir = sync_skill_to_workspace()
    # 渲染 hook 模板，将占位符替换为实际安装路径
    render_hook_templates(workspace_skill_dir)
    setup_runtime_hooks()

    if update_openclaw_config(workspace_skill_dir):
        print("Restarting OpenClaw gateway...")
        try:
            subprocess.run(['openclaw', 'gateway', 'restart'], check=True)
            print("Gateway restarted.")
        except Exception as e:
            print(f"Could not restart gateway automatically: {e}")

    # Run self-check
    check_script = SOURCE_DIR / 'scripts' / 'check_activation.py'
    if check_script.exists():
        print("\nRunning activation self-check...")
        subprocess.run(['python3', str(check_script)])

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
