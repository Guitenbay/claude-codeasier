---
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

- Parse `$ARGUMENTS` by whitespace.
- The first token is `mode` and must be `troubleshoot` or `summary`.
- The second token is optional `session-id`.
- Any remaining text is optional `focus`.

If mode is missing or not `troubleshoot|summary`, output exactly:

```text
用法: /session:review <troubleshoot|summary> [session-id] [focus]
```

Do not do anything else.

## Session selection

This command is usually used from a new session to review a historical session.

- If `session-id` is provided, review that explicit historical session id.
- If `session-id` is omitted, review the current session. Use `${CLAUDE_SESSION_ID}` as the session id.
- Never replace an explicit `session-id` with the current session id.

## SOP loading

Always read `${CLAUDE_SKILL_DIR}/shared.sop` first.

Then:

- If `mode` is `troubleshoot`, read `${CLAUDE_SKILL_DIR}/troubleshoot.sop`.
- If `mode` is `summary`, read `${CLAUDE_SKILL_DIR}/summary.sop`.

After reading the SOP files:

1. Resolve the target session file.
   - Prefer `~/.claude/plugins/session/state/session-index.json`.
   - If missing there, search under `~/.claude/projects/` for the target session id.
2. Treat `focus` as the analysis focus if provided.
3. Follow the shared SOP and mode-specific SOP strictly.
4. Output only the review result, not the SOP contents.
