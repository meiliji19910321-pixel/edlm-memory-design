---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

**Personal skills live in agent-specific directories (`~/.claude/skills` for Claude Code, `~/.agents/skills/` for Codex)**

You write test cases (pressure scenarios with subagents), watch them fail (baseline behavior), write the skill (documentation), watch tests pass (agents comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** You MUST understand superpowers:test-driven-development before using this skill. That skill defines the fundamental RED-GREEN-REFACTOR cycle. This skill adapts TDD to documentation.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools. Skills help future Claude instances find and apply effective approaches.

**Skills are:** Reusable techniques, patterns, tools, reference guides

**Skills are NOT:** Narratives about how you solved a problem once

## TDD Mapping for Skills

| TDD Concept | Skills Analogy |
|-------------|----------------|
| Write failing test | Write skill description + test scenario |
| Watch it fail | Subagent fails without skill guidance |
| Write minimal code | Write skill documentation |
| Watch it pass | Agent follows skill guidance |
| Refactor | Close loopholes, improve clarity |

## Skill Structure

```
skills/
└── skill-name/
    └── SKILL.md
```

## SKILL.md Format

```markdown
---
name: skill-name
description: One-line description of when to use this skill
---

# Skill Title

## Overview
[What this skill does]

## When to Use
[When to invoke this skill]

## How to Use
[Step-by-step guidance]

## Anti-Patterns
[What NOT to do]
```

## Testing Your Skill

1. Remove the skill temporarily
2. Run a scenario that should trigger the skill
3. Verify the agent fails to follow the expected behavior
4. Add the skill
5. Run the scenario again
6. Verify the agent now follows the expected behavior

## Installation

This skill is part of Superpowers. See: https://github.com/obra/superpowers
