---
name: review
description: Review a historical Claude Code session by session id, or review the current session only when no session id is provided.
disable-model-invocation: true
argument-hint: <troubleshoot|summary> [session-id] [focus]
allowed-tools: Read, Glob, Grep, Bash
---

You are the `session:review` entrypoint.

## Usage

```text
/session:review <troubleshoot|summary> [session-id] [focus]
```

- `$1` is `mode` and must be `troubleshoot` or `summary`.
- `$2` is optional `session-id`.
- `$3` is optional `focus`.

If mode is missing or not `troubleshoot|summary`, output exactly:

```text
用法: /session:review <troubleshoot|summary> [session-id] [focus]
```

Do not do anything else.

## Session selection

This command is usually used from a new session to review a historical session.

- If `$2` is provided, review that explicit historical session id.
- If `$2` is omitted, review the current session. Use `${CLAUDE_SESSION_ID}` as the session id.
- Never replace an explicit `$2` session id with the current session id.

## SOP loading

Always read `${CLAUDE_SKILL_DIR}/shared.sop` first.

Then:

- If `$1=troubleshoot`, read `${CLAUDE_SKILL_DIR}/troubleshoot.sop`.
- If `$1=summary`, read `${CLAUDE_SKILL_DIR}/summary.sop`.

After reading the SOP files:

1. Resolve the target session file.
   - Prefer `~/.claude/plugins/session/state/session-index.json`.
   - If missing there, search under `~/.claude/projects/` for the target session id.
2. Treat `$3` as the analysis focus if provided.
3. Follow the shared SOP and mode-specific SOP strictly.
4. Output only the review result, not the SOP contents.
