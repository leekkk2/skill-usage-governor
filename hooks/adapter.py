#!/usr/bin/env python3
import json
import sys
import subprocess
from pathlib import Path

# Path to the record_usage script
BASE_DIR = Path(__file__).resolve().parents[1]
RECORD_SCRIPT = BASE_DIR / 'scripts' / 'record_usage.py'

def record(skill_name, source, role='assistant'):
    if not skill_name:
        return
    cmd = [sys.executable, str(RECORD_SCRIPT), skill_name, source, role]
    subprocess.run(cmd, capture_output=True)

def handle_gemini(data):
    # Gemini CLI Hook input format
    # { "event": "AfterTool", "matcher": "activate_skill", "tool_input": { "name": "xxx" }, ... }
    tool_name = data.get('matcher') or data.get('tool_name')
    if tool_name == 'activate_skill':
        skill_name = data.get('tool_input', {}).get('name')
        record(skill_name, 'gemini-cli')

def handle_claude(data):
    # Claude Code Hook input format (based on cchooks docs)
    # { "hook_event_name": "PostToolUse", "tool_name": "activate_skill", "tool_input": { "name": "xxx" }, ... }
    tool_name = data.get('tool_name')
    if tool_name == 'activate_skill':
        skill_name = data.get('tool_input', {}).get('name')
        record(skill_name, 'claude-code')

def handle_windsurf(data):
    # Windsurf / Cascade Hook input format
    # { "event": "post-tool-use", "tool": "activate_skill", "arguments": { "name": "xxx" }, ... }
    tool_name = data.get('tool')
    if tool_name == 'activate_skill':
        skill_name = data.get('arguments', {}).get('name')
        record(skill_name, 'windsurf-cascade')

def handle_vibe(data):
    # Vibe CLI format
    # { "tool": "activate_skill", "input": { "name": "xxx" } }
    tool_name = data.get('tool')
    if tool_name == 'activate_skill':
        skill_name = data.get('input', {}).get('name')
        record(skill_name, 'vibe-cli')

def main():
    source_hint = sys.argv[1] if len(sys.argv) > 1 else 'auto'
    
    try:
        raw_input = sys.stdin.read()
        if not raw_input:
            # If no stdin, maybe it's passed via args (fallback)
            if len(sys.argv) > 2:
                record(sys.argv[2], source_hint)
            return

        data = json.loads(raw_input)
        
        # Dispatch based on source_hint or data structure
        if source_hint == 'gemini' or 'matcher' in data:
            handle_gemini(data)
        elif source_hint == 'claude' or 'hook_event_name' in data:
            handle_claude(data)
        elif source_hint == 'windsurf' or 'arguments' in data:
            handle_windsurf(data)
        elif source_hint == 'vibe' or ('tool' in data and 'input' in data):
            handle_vibe(data)
        else:
            # Generic fallback
            tool_name = data.get('tool') or data.get('tool_name')
            if tool_name == 'activate_skill':
                skill_name = (data.get('arguments') or data.get('tool_input') or data.get('input') or {}).get('name')
                record(skill_name, f'vibe-coding-cli-{source_hint}')

    except Exception as e:
        # Hooks should fail silently to not block the agent
        print(f"Error in hook adapter: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
