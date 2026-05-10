---
name: using-git-worktrees
description: Use when you need to work on multiple features in parallel
---

# Using Git Worktrees

## Overview

Worktrees let you work on multiple branches simultaneously without stashing or switching context.

## When to Use

- Working on multiple features concurrently
- Needing to keep main branch clean while working
- Code review that requires context switching

## Basic Commands

### Create a worktree
```bash
git worktree add <branch-name> -b <new-branch-name>
```

### List worktrees
```bash
git worktree list
```

### Remove a worktree
```bash
git worktree remove <branch-name>
```

## Workflow

1. Create worktree from clean main branch
2. Run project setup in new worktree
3. Verify clean test baseline
4. Implement task
5. Complete worktree when done

## Anti-Patterns

### Don't Work on Multiple Tasks in Same Worktree

Each worktree = one task = one branch.

### Don't Forget to Remove Worktrees

Accumulated worktrees clutter your filesystem.

## Installation

This skill is part of Superpowers. See: https://github.com/obra/superpowers
