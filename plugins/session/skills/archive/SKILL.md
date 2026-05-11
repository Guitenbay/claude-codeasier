---
description: Archive a Claude Code session transcript. For active sessions, marks as pending-archive (deferred until session ends). Use "archive cancel" to revert.
disable-model-invocation: true
argument-hint: [session-id | cancel]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py *)
---

Run:

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py archive $ARGUMENTS
```
