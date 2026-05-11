---
description: Delete or trash a Claude Code session transcript by session id, or target the current session when no id is provided.
disable-model-invocation: true
argument-hint: [session-id]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py *)
---

Run:

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py delete $ARGUMENTS
```
