---
name: writing-plans
description: Use when you have an approved design and need to break it into implementation tasks
---

# Writing Plans

## Overview

Transform approved designs into detailed, actionable implementation plans.

Every task in a plan should be:
- 2-5 minutes of work
- Have exact file paths
- Include complete code
- Specify verification steps

## When to Use

When you have an approved design and need to create an implementation plan.

## Plan Format

```markdown
## Task: <task-name>

### File(s)
- `path/to/file.ext`

### What to do
[Specific action with exact details]

### Verification
[How to verify the task is complete]
```

## Anti-Patterns

### Don't Write Vague Tasks

"Implement the user module" is not a task. "Create UserService class with login/logout methods" is a task.

### Don't Write Tasks Without File Paths

Every task must specify exactly which files to modify.

### Don't Write Tasks That Take Hours

Break large tasks into 2-5 minute chunks. If a task takes more than 10 minutes, it's probably multiple tasks.

## Installation

This skill is part of Superpowers. See: https://github.com/obra/superpowers
