---
description: Configure the session plugin, including archive and trash directories.
disable-model-invocation: true
argument-hint: [archive-dir|trash-dir|show|reset] [value]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py *)
---

Run:

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/cc_session.py setup $ARGUMENTS
```
