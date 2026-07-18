---
name: skill-name
description: One sentence describing what this skill does and when to invoke it.
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
from pydantic.dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True, kw_only=True)
class ExampleParams:
    """
    Parameters for the example operation.

    Fields:
        field_one: Description of field_one.
        field_two: Description of field_two.
    """

    field_one: str
    field_two: int = 0


def example_function(input: ExampleParams) -> Dict[str, Any]:
    """
    Do the thing this skill is about.

    Args:
        input: ExampleParams with field_one and field_two.

    Returns:
        Dict[str, Any]: {"result": ...}
    """
    ...
```

---

## Variations

### Variation A — when condition X applies

```python
# Annotated example for variation A
```

**Key points:**
- Point one
- Point two

### Variation B — when condition Y applies

```python
# Annotated example for variation B
```

**Key points:**
- Point one
- Point two

---

## Rules

- ✅ Always do X
- ✅ Always do Y
- ❌ Never do Z
- ❌ Never do W

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
