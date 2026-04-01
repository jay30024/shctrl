# Git Maintenance Playbook

This standard playbook covers safe workspace cleanup and branch hygiene.

## Preview Untracked Files

Use a dry run before any destructive cleanup:

```bash
git clean -nd
```

## Delete Untracked Files

Only after reviewing the preview output:

```bash
git clean -fd
```

## Verify State

```bash
git status --short
```
