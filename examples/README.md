# examples

`examples/` is the official test fixture directory for `scripts/check_rules.py`.

Current fixture responsibilities:

- `rule-check.json`
  - Strict baseline failure sample
  - Retains historical-compatible name
  - Coverage: in standard strict mode, failure to read `SKILL.md` causes blocking

- `rule-check-pass.json`
  - Strict success sample
  - Coverage: reading before using passes the check as per rules

- `strict-fail.json`
  - Strict + whitelist failure path sample
  - Coverage: protected/whitelisted skills should be skipped, but non-whitelisted unread skills are still blocked

- `lenient-warn.json`
  - Lenient warning baseline sample
  - The only remaining lenient warning fixture
  - No other historical lenient duplicate samples are retained
  - Coverage: failure to read `SKILL.md` triggers a warning but does not block

Notes:
- This directory retains only 4 official test fixtures: `rule-check.json`, `rule-check-pass.json`, `strict-fail.json`, `lenient-warn.json`.
- `rule-check.json` and `strict-fail.json` are not duplicate samples.
- The former verifies "standard strict unread blocking"; the latter verifies "strict + whitelist blocks only non-whitelisted skills".
- If further fixture pruning is needed, prioritize keeping "one fixture per independent semantic case".
- When adding, replacing, or removing fixtures, this file's fixture list and responsibility descriptions must be updated accordingly to prevent directory contents from drifting out of sync with documentation.
- If a fixture's responsibility changes, even if the filename stays the same, the corresponding entry description must be updated — changing fixture content without updating the description is not allowed.
