---
name: skill-name
description: One sentence describing what this skill does AND when Claude should invoke it. This text is the only thing Claude sees when deciding whether to load the skill, so lead with concrete trigger words (e.g. "Use when creating a new Temporal activity...").
---

# Skill Title

One or two sentences describing the purpose of this skill and what it helps Claude do.

---

## When to Use

- Use when asked to **X**
- Use when **Y** needs to be created or modified
- Do NOT use for **Z** (use `other-skill` instead)

---

## Steps

1. **Step one** — brief description
2. **Step two** — brief description
3. **Step three** — brief description

---

## Standard Pattern

```python
# Minimal working example that follows the project standard
```

---

## Rules

- ✅ Always do X
- ❌ Never do Z

---

## After Creation

1. **Register / wire up** — where to add the new file (worker, router, `__init__.py`, etc.)
2. **Test** — how to verify the result works
3. **Related skills** — link to `other-skill` if follow-up work is common

---

## Checklist

- [ ] Follows the standard pattern above
- [ ] Includes a docstring on every public function/class
- [ ] Registered in the correct worker or router
- [ ] Tested against the running service
