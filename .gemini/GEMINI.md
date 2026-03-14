# GSD Methodology — Mission Control Rules

> **Get Shit Done**: A spec-driven, context-engineered development methodology.
> 
> These rules enforce disciplined, high-quality autonomous development.

---

## Canonical Rules

**All canonical rules are in [PROJECT_RULES.md](../PROJECT_RULES.md).**

This file provides Gemini-specific integration. For the complete methodology, see PROJECT_RULES.md.

---

## Core Principles

1. **Plan Before You Build** — No code without specification
2. **State Is Sacred** — Every action updates persistent memory
3. **Context Is Limited** — Prevent degradation through hygiene
4. **Verify Empirically** — No "trust me, it works"

---

## 5. Terminal Command Protocol (STRICT ATOMIC EXECUTION)

You are strictly forbidden from issuing multiple commands in a single tool execution. You must operate the terminal interactively, one step at a time. **Do not attempt to save tokens or tool calls by batching commands.**

- **One Command Per Tool Call:** You must execute exactly ONE single-line terminal command, wait for the terminal output, and verify the result before issuing the next command.
- **No Inline Chaining:** Do NOT use `;`, `&&`, or `||`.
- **No Multi-Line Scripts:** Do NOT submit multiple commands separated by newlines (`\n`) or carriage returns. Your tool input must be a single, flat string.
- **Example of FORBIDDEN behavior (Token-saving batching):**
  ```bash
  git add .gsd/STATE.md
  git commit -m "docs: update state"
  ```
- **Example of REQUIRED behavior (Atomic execution):**
  1. Call terminal tool with: `git add .gsd/STATE.md`
  2. Wait for response.
  3. Call terminal tool with: `git commit -m "docs: update state"`

---


## Quick Reference

```
Before coding    → Check SPEC.md is FINALIZED
Before file read → Search first, then targeted read
After each task  → Update STATE.md
After 3 failures → State dump + fresh session
Before "Done"    → Empirical proof captured
```

---

## Workflow Integration

These rules integrate with the GSD workflows:

| Workflow | Rules Enforced |
|----------|----------------|
| `/map` | Updates ARCHITECTURE.md, STACK.md |
| `/plan` | Enforces Planning Lock, creates ROADMAP |
| `/execute` | Enforces State Persistence after each task |
| `/verify` | Enforces Empirical Validation |
| `/pause` | Triggers Context Hygiene state dump |
| `/resume` | Loads state from STATE.md |

---

## Gemini-Specific Tips

For Gemini-specific enhancements, see [adapters/GEMINI.md](../adapters/GEMINI.md).

Key recommendations:
- **Flash** for quick iterations and simple edits
- **Pro** for complex planning and analysis
- Large context is available but **search-first** still applies

---

*GSD Methodology adapted for Google Antigravity*
*Canonical rules: [PROJECT_RULES.md](../PROJECT_RULES.md)*
*Source: https://github.com/glittercowboy/get-shit-done*

