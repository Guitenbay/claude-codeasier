# claude-codeasier

A Claude Code plugin marketplace for reusable workflow and productivity plugins.

Current plugins:

- `session`
- `dev`
- `docs`
- `release`

## Marketplace usage

### Local repository

Add this marketplace from the current repository:

```text
/plugin marketplace add .
```

### Remote repository

Add this marketplace from GitHub:

```text
/plugin marketplace add codeasier/claude-codeasier
```

Install `session`:

```text
/plugin install session@claude-codeasier
/reload-plugins
```

For other plugins, replace `session` with one of: `dev`, `docs`, `release`.

- `session`: `plugins/session/README.md`
- `dev`: `plugins/dev/README.md`
- `docs`: `plugins/docs/README.md`
- `release`: `plugins/release/README.md`

## Repository structure

```text
claude-codeasier/
├── .claude-plugin/marketplace.json
└── plugins/
    ├── session/
    ├── dev/
    ├── docs/
    └── release/
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
