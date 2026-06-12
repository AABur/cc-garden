# cc-garden — Project Configuration

cc-garden is the development repository for Claude Code plugins and skills that are
published through the marketplace. The global `~/.claude/CLAUDE.md` rules apply; the
rule below is specific to this repo.

## Development vs Installation

- Keep development and installation strictly separate. Develop and publish plugins/skills
  in this repository, and install them onto a machine only through the proper marketplace
  mechanism — never mix the two.
- Never wire this dev repo into the live `~/.claude` install via symlinks or manual copies.
  The repository can move or change, so a manual link is a footgun, not a setup step.
