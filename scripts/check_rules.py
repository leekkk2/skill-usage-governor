#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_rules.py <input.json>")
        return 2

    p = Path(sys.argv[1])
    data = json.loads(p.read_text(encoding="utf-8"))
    policy = data.get("policy", "strict")
    skill_calls = data.get("skillCalls", [])
    whitelist = set(data.get("whitelist", []))

    failed = []
    warnings = []

    for call in skill_calls:
        skill = call.get("skill", "<unknown>")
        read = bool(call.get("read", False))
        path = call.get("path", "")
        if skill in whitelist:
            continue
        if not read:
            msg = {
                "skill": skill,
                "path": path,
                "reason": "SKILL.md not read before usage"
            }
            if policy == "strict":
                failed.append(msg)
            else:
                warnings.append(msg)

    result = {
        "policy": policy,
        "checked": len(skill_calls),
        "status": "pass" if not failed else "fail",
        "failed": failed,
        "warnings": warnings
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
