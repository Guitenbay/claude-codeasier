---
description: Archive a Claude Code session transcript by session id, or archive the current session when no id is provided.
disable-model-invocation: true
argument-hint: [session-id]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py *)
---

Run:

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py archive $ARGUMENTS
```
