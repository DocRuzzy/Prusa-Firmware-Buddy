# Copilot Working Notes

> **All project guidance lives in [AGENT.md](../AGENT.md).**
> This file contains only GitHub Copilot-specific notes. Read AGENT.md first!

## Required Reading Order

1. **[AGENT.md](../AGENT.md)** - Universal project instructions (build procedures, tool config, completed fixes, pitfalls, architecture)
2. **[TODO.md](../TODO.md)** - Current task list and status

## Copilot-Specific Notes

### Context Loading
When Copilot Chat opens this file via `.github/copilot-instructions.md`, it should treat [AGENT.md](../AGENT.md) as the primary instruction source. All build procedures, tool configuration details, completed fix history, known pitfalls, code architecture diagrams, and future development plans are maintained there.

### Quick Reference
- **Project**: Prusa XL firmware with custom syringe dispenser tool (T4)
- **Build**: `cd build/xl_release_boot && cmake --build . --target firmware -j$(nproc)`
- **Output**: Always copy `.bbf` (4MB), never `.bin` (2MB)
- **Tool indices**: Buddy `e == 4`, DWARF `dwarf_nr == 5`
- **Full details**: See [AGENT.md](../AGENT.md)
