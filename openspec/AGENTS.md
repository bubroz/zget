# OpenSpec Agent Instructions

These instructions explain how AI assistants should use OpenSpec in this project.

## When to Use OpenSpec

Use OpenSpec when:

- Adding new platform support
- Changing the API (download function signature)
- Adding new CLI options
- Major refactoring

Skip OpenSpec for:

- Bug fixes
- Documentation updates
- Small code improvements

## Directory Structure

```
openspec/
├── project.md      # Project context and conventions
├── specs/          # Capability specifications (what zget does)
└── changes/        # Change proposals (what we're adding/changing)
```

## Creating a Change Proposal

1. Create folder: `openspec/changes/add-<feature>/`
2. Add `proposal.md` with Why/What/Impact
3. Add `tasks.md` with checklist
4. Implement the change
5. Archive when done

## Quick Reference

```bash
# Validate specs and changes
npx openspec validate

# Create a new change
mkdir openspec/changes/add-my-feature
```
