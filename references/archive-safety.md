# Archive Safety

## Design Principles

Archive operations follow a "recoverability first" principle — users can always restore to the pre-archive state if anything goes wrong.

## Archive Workflow

```
1. dry-run        → List archive candidates without making any changes
2. User confirms  → Agent must not skip the confirmation step
3. Move files     → skills/<name> → skills_archive/<name>
4. Generate manifest → Records source path, timestamp, and restore command
5. Restore        → restore.py --skill <name> performs the reverse operation
```

## Protection Layers

| Layer | Mechanism |
|-------|-----------|
| **Protected whitelist** | Skills listed in `policy.yaml` under `protected_skills` are never considered for archiving |
| **Dry-run by default** | `archive.dry_run_default: true` — even direct script execution won't perform real operations |
| **User confirmation** | Agent must show dry-run results and obtain user confirmation before executing |
| **Manifest record** | Each archive generates a JSON manifest with complete restore information |
| **Recoverable** | `restore.py` moves the skill back to its original location based on the manifest |

## What Will Never Happen

- Files will never be permanently deleted
- Archiving will never execute without user confirmation
- Protected skills will never be archived
- The file system will never be modified in dry-run mode
- Manifests will never be lost (stored inside the archive directory)

## Restore Workflow

```bash
# List archived skills
ls skills_archive/

# Restore a specific skill
python3 scripts/restore.py --skill <name>

# Verify after restore
ls skills/<name>/SKILL.md
```
