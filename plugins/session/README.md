# session

Manage Claude Code session transcripts with archive, trash, and lifecycle hooks.

## What it does

- Tracks Claude Code sessions via `SessionStart` and `SessionEnd` hooks
- Stores a local session index under `~/.claude/plugins/session/state/`
- Archives session transcripts
- Moves ended session transcripts to trash or purges them
- Exposes namespaced skills:
  - `/session:archive [session-id]`
  - `/session:delete [session-id]`
  - `/session:review <troubleshoot|summary> [session-id] [focus]`
  - `/session:setup ...`

## Plugin structure

```text
session/
├── .claude-plugin/plugin.json
├── hooks/hooks.json
├── skills/
└── scripts/
```

## Local development

Run Claude Code with the plugin directly:

```bash
claude --plugin-dir ./plugins/session
```

Then reload plugins if needed:

```text
/reload-plugins
```

## Install from marketplace

If you are using the local `claude-codeasier` marketplace in this repository:

```text
/plugin marketplace add .
/plugin install session@claude-codeasier
/reload-plugins
```

## Commands

### Archive a session

Archive the current active session:

```text
/session:archive
```

Archive a specific session:

```text
/session:archive <session-id>
```

Behavior:

- active session: copies transcript into archive
- ended session: moves transcript into archive

### Delete a session

Delete or trash a specific ended session:

```text
/session:delete <session-id>
```

Behavior:

- active session: refused
- ended session: moved to trash by default

### Review a session

Review a historical session by explicit id:

```text
/session:review summary <session-id>
/session:review troubleshoot <session-id> [focus]
```

If `session-id` is omitted, the command reviews the current session:

```text
/session:review summary
```

This command usually runs in a new session to analyze a historical transcript. It first checks `~/.claude/plugins/session/state/session-index.json`, then falls back to searching `~/.claude/projects/`.

### Configure the plugin

Show config:

```text
/session:setup show
```

Set archive directory:

```text
/session:setup archive-dir ~/.claude/projects/${project_slug}/.archive/sessions
```

Set trash directory:

```text
/session:setup trash-dir ~/.claude/projects/${project_slug}/.trash/sessions
```

Reset config:

```text
/session:setup reset
```

Reset one key:

```text
/session:setup reset archive-dir
/session:setup reset trash-dir
```

## Config

Config is stored in:

```text
~/.claude/plugins/session/state/config.json
```

Current supported keys:

- `archiveDir`
- `trashDir`
- `defaultDeleteMode`
- `archiveCurrentSessionMode`

Defaults:

- `archiveDir = ~/.claude/projects/${project_slug}/.archive/sessions`
- `trashDir = ~/.claude/projects/${project_slug}/.trash/sessions`
- `defaultDeleteMode = trash`
- `archiveCurrentSessionMode = copy`

## Session index

Session state is stored in:

```text
~/.claude/plugins/session/state/session-index.json
```

## Notes

When passing `${project_slug}` in a shell command, quote the string so your shell does not expand it before `session` receives it:

```bash
!python3 session/scripts/cc_session.py setup archive-dir '~/.claude/projects/${project_slug}/.archive/sessions'
```
