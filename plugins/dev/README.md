# dev

Developer workflow helpers for environment setup, issues, pull requests, and git worktrees.

## Included skills

- `/dev:env-setup [extra-env ...]`
- `/dev:issue-resolve <issue-num>`
- `/dev:issue-review <issue_num>`
- `/dev:issue-submit <owner/repo>`
- `/dev:pr-followup <pr-number> [focus]`
- `/dev:worktree-clean`

## Local development

```bash
claude --plugin-dir ./plugins/dev
```

## Install from local marketplace

```text
/plugin marketplace add .
/plugin install dev@claude-codeasier
/reload-plugins
```
