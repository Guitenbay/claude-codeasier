# claude-codeasier

A Claude Code plugin marketplace for reusable workflow and productivity plugins.

Current plugins:

- `session-keeper`

## Local marketplace usage

Add this marketplace from the current repository:

```text
/plugin marketplace add ./claude-codeasier
```

Install `session-keeper`:

```text
/plugin install session-keeper@claude-codeasier
/reload-plugins
```

## Repository structure

```text
claude-codeasier/
├── .claude-plugin/marketplace.json
└── plugins/
    └── session-keeper/
```

## Marketplace name

The marketplace identifier is:

```text
claude-codeasier
```

The shorthand `cce` is a convenient nickname for documentation and discussion, but installs should use the full marketplace name.

## Adding more plugins

Add a new plugin under:

```text
claude-codeasier/plugins/<plugin-name>/
```

Then register it in:

```text
claude-codeasier/.claude-plugin/marketplace.json
```

## Remote usage

Once this directory is pushed to a git repository containing `.claude-plugin/marketplace.json`, users can add it with:

```text
/plugin marketplace add <owner>/<repo>
```

Then install plugins by name:

```text
/plugin install <plugin-name>@claude-codeasier
```
