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

You are strictly forbidden from executing multiple operations in a single tool call. You must operate the terminal interactively, one step and one target at a time. **Do not attempt to save tokens by batching commands or arguments.**

- **One Command Per Tool Call:** You must execute exactly ONE single-line terminal command, wait for the terminal output, and verify the result before issuing the next command.
- **No Inline Chaining:** Do NOT use `;`, `&&`, or `||`.
- **No Multi-Line Scripts:** Do NOT submit multiple commands separated by newlines (`\n`) or carriage returns. Your tool input must be a single, flat string.
- **No Multi-Target Argument Batching:** When inspecting files, listing directories, or reading state, do NOT pass multiple files as comma-separated or space-separated lists. Inspect one file or directory per command.

**Examples of FORBIDDEN behavior (Token-saving batching):**
- *Multi-line:*
  `git add .gsd/STATE.md\ngit commit -m "docs"`
- *Argument chaining:*
  `dir .gsd/ROADMAP.md, .gsd/STATE.md`
  `cat file1.py file2.py`
- *Operator chaining:*
  `uv init ; uv add pytest`

**Examples of REQUIRED behavior (Atomic execution):**
1. Call terminal tool with: `dir .gsd/ROADMAP.md`
2. Wait for response.
3. Call terminal tool with: `dir .gsd/STATE.md`
4. Wait for response.

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

