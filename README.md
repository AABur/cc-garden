# cc-garden

Personal Claude Code plugin marketplace.

## Add as marketplace

```
/plugin marketplace add cc-garden github:AABur/cc-garden
```

## Available plugins

| Plugin | Description |
|--------|-------------|
| [new-python-project](plugins/new-python-project/) | Bootstrap a production-ready Python project end-to-end |

## Install a plugin

```
/plugin install <plugin-name>@cc-garden
```

## Structure

```
cc-garden/
└── plugins/
    └── <plugin-name>/
        ├── .claude-plugin/
        │   └── plugin.json    # metadata
        ├── skills/            # skill definitions
        └── README.md
```
