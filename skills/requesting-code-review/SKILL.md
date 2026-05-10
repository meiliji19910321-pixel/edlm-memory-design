---
name: requesting-code-review
description: Use before requesting a code review from team members
---

# Requesting Code Review

## Overview

Review your own code before requesting review from others. This saves everyone's time and produces better outcomes.

## Checklist

Before requesting review:

1. **Verify against spec** — Does code match the approved design?
2. **Check tests** — Do tests pass? Are they meaningful?
3. **Self-review** — Read every line you changed
4. **No placeholder comments** — No "TODO: fix later" or "placeholder code"
5. **Clean commit** — Changes are atomic and message is descriptive

## Review Report Format

When reporting issues, organize by severity:

```
## Critical Issues (Block Merge)
- [Issue with exact location and fix]

## Warnings (Should Fix)
- [Issue with suggestion]

## Suggestions (Nice to Have)
- [Improvement idea]
```

## Anti-Patterns

### Don't Request Review Without Self-Review

If you haven't verified your own code, you're wasting the reviewer's time.

### Don't Submit Incomplete Work

"It's mostly done, just need to fix X" blocks everyone.

## Installation

This skill is part of Superpowers. See: https://github.com/obra/superpowers
