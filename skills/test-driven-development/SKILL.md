---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask your human partner):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The RED-GREEN-REFACTOR Cycle

### RED: Write the Failing Test

1. Write a test that describes the behavior you want
2. Run the test and watch it fail
3. If the test passes on first run, you're not testing the right thing

### GREEN: Write Minimal Code

1. Write the smallest amount of code to make the test pass
2. No abstractions, no "cleaning up"
3. Just enough to make the test green

### REFACTOR: Clean Up

1. Now that tests pass, improve the code
2. Extract abstractions
3. Remove duplication
4. Ensure tests still pass

## Anti-Patterns

### Don't Write Implementation Before Tests

If you write code before tests:
- You're not testing what you think you're testing
- You're likely testing that the code works, not that it should work
- You lose the design guidance that TDD provides

### Don't Skip the "Watch it Fail" Step

"Tests passing on first run" means you wrote a broken test or no test at all.

### Don't Write Code After Tests Pass

This is "programming by coincidence." Write code in response to failing tests only.

### Don't Test Internal Implementation Details

Test observable behavior, not how it's implemented.

### Don't Write Integration Tests Before Unit Tests

Start with the smallest, fastest tests first.

## Installation

This skill is part of Superpowers. See: https://github.com/obra/superpowers
