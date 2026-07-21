---
name: docstring-formatter
description: Format or rewrite Python docstrings to match the project standard. Use when asked to add, fix, or standardize docstrings on functions, methods, classes, or dataclasses.
---

# Docstring Formatter

Use this skill to write or rewrite Python docstrings to match the project's standard format.

## Standard Format

```python
"""
<description or summary sentence(s)>.

Args:
    param_name: <description of the parameter>.
    param_name: <description of the parameter>.

Returns:
    type: <short description or example of the return value>.
"""
```

### Rules

- **Summary line**: one or two sentences, plain English, no trailing period required on single-line summaries inside a multi-section docstring.
- **Args section**: include only when the function has parameters. Each entry is `param_name: description` — no type annotation (type is already in the signature).
  - Does not apply within "...Params" dataclass docstrings, where the field definitions should be called "Fields" and the docstring describes the overall purpose of the dataclass.
- **Returns section**: include only when the function returns a non-`None` value. Format is `type: description_or_example`.
- **Blank line** between the summary and `Args:`, and between `Args:` and `Returns:`.
- No `Raises:` section unless the function deliberately raises a documented exception.
- Opening `"""` is on its own line (multi-line docstring), closing `"""` is on its own line.

---

## Examples

### Simple function

```python
async def get_league_data(input: GetLeagueDataParams) -> Dict[str, Any]:
    """
    Fetch league metadata, rosters, and users from the Sleeper API.

    Args:
        input: League ID and optional season filter.

    Returns:
        Dict[str, Any]: {"league_info": {...}, "league_rosters": [...], "league_users": [...]}
    """
```

### Dataclass (from pydantic.dataclasses)

```python
@dataclass(frozen=True, kw_only=True)
class PrepareOwnerTrainingDataParams:
    """
    Parameters for preparing training data for a single team owner's model.

    Args:
        league_id: Sleeper league identifier.
        user_id: Sleeper user identifier of the team owner.
        season: Season year filter, e.g. "2025". None includes all seasons.
        adp_data: Pre-computed ADP dict from calculate_adp_from_picks. None triggers a default.
        min_picks_required: Minimum historical picks needed before training proceeds.
    """
    league_id: str
    user_id: str
    season: Optional[str] = None
    adp_data: Optional[Dict[str, Any]] = None
    min_picks_required: int = 10
```

### Method with multiple return fields

```python
async def prepare_owner_training_data(
    input: PrepareOwnerTrainingDataParams,
) -> Dict[str, Any]:
    """
    Prepare encoded training samples and the owner profile for model training.

    Fetches DraftPick, Draft, Player, and TeamOwner records, reconstructs draft
    context at each pick, encodes player features, and computes the 26-dim owner
    profile vector.

    Args:
        input: Params containing league_id, user_id, optional season, optional
               ADP data, and minimum-picks threshold.

    Returns:
        Dict[str, Any]: {
            "training_samples": [{"pick_no": int, "round": int, "candidate_features": [...], ...}],
            "owner_profile": [float, ...],
            "num_samples": int,
            "user_id": str,
            "league_id": str,
            "season": str | None,
        }
    """
```

### No args, no return (side-effect / lifecycle function)

```python
async def lifespan(app: FastAPI):
    """
    Manage Temporal client lifecycle for the FastAPI application.

    Connects on startup and closes the client on shutdown.
    """
```

---

## Checklist before finishing

- [ ] Summary is accurate and written in plain English.
- [ ] Every non-`self` parameter has an entry in `Args:`.
- [ ] `Returns:` type matches the function's return annotation.
- [ ] No type annotations duplicated inside the docstring body (they belong in the signature).
- [ ] Blank lines separate summary, `Args:`, and `Returns:` sections.
- [ ] Closing `"""` is on its own line.
