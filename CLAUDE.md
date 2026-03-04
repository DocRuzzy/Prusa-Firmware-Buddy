# Claude CLI Instructions - Prusa Firmware Buddy

> **All project guidance lives in [AGENT.md](AGENT.md).**
> This file contains only Claude CLI-specific notes. Read AGENT.md first!

## Required Reading Order

1. **[AGENT.md](AGENT.md)** - Universal project instructions (build procedures, tool config, completed fixes, pitfalls, architecture)
2. **[TODO.md](TODO.md)** - Current task list and status

## Claude-Specific Notes

### Permissions
This project grants Claude CLI access to:
- File reading/writing
- Terminal commands (builds, git operations)
- Workspace search

See `.claude/settings.local.json` for detailed permissions.
