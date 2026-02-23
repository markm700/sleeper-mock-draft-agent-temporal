import os
from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Dict, Optional
from temporalio import workflow
from temporalio.common import RetryPolicy


def _safe_slug(text: str | None) -> str:
    """Create a simple, deterministic slug for workflow IDs.

    Uses only lowercase ASCII letters, digits, and dashes.
    """

    if not text:
        return "value"

    cleaned: list[str] = []
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch.lower())
        else:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    return slug or "value"


with workflow.unsafe.imports_passed_through():
    from workflows.team_owner_data_collection import (
        TeamOwnerDataCollectionWorkflow,
        TeamOwnerDataCollectionWorkflowParams,
    )
    from workflows.league_data_collection import (
        LeagueDataCollectionWorkflow,
        LeagueDataCollectionWorkflowParams,
    )


@dataclass
class FullDataCollectionWorkflowParams:
    """Input parameters for the combined team owner + league data workflow.

    Attributes:
        username: Sleeper username for the team owner.
        league_name: Human-readable league name used to filter leagues.
    """

    username: str
    league_name: str


@workflow.defn(name="full-data-collection")
class FullDataCollectionWorkflow:
    """Workflow that chains team owner data collection with league data collection.

    It first runs the team-owner-data-collection workflow to resolve the
    appropriate league for the given user and league name, then runs the
    league-data-collection workflow for that league.
    """

    @workflow.run
    async def run(self, params: FullDataCollectionWorkflowParams) -> Dict[str, Any]:
        wf_hex = os.urandom(4).hex()
        child_workflow_results: list[Dict[str, Any]] = []
        child_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(minutes=5),
            maximum_interval=timedelta(minutes=10),
            backoff_coefficient=2.0,
        )

        # Step 1: Run team-owner-data-collection as a child workflow
        owner_result: Dict[str, Any] = await workflow.execute_child_workflow(
            TeamOwnerDataCollectionWorkflow.run,
            TeamOwnerDataCollectionWorkflowParams(
                username=params.username,
                league_name=params.league_name,
            ),
            id=f"child_workflow-team_owner_data_collection-{params.username}-{_safe_slug(params.league_name)}-{wf_hex}",
            retry_policy=child_retry_policy,
            run_timeout=timedelta(minutes=30),
            execution_timeout=timedelta(minutes=60),
            task_timeout=timedelta(minutes=10),
        )
        child_workflow_results.append(
            {
                "workflow": "team-owner-data-collection",
                "result": owner_result,
            }
        )

        # Extract the target league_id for the provided league_name
        league_id: Optional[str] = None
        team_owner_core: Optional[Dict[str, Any]] = None
        for entry in owner_result.get("activity_data", []):
            if entry.get("activity") == "get_team_owner_data":
                team_owner_core = entry.get("result")
                break
        if team_owner_core is None:
            raise ValueError("Workflow team-owner-data-collection result missing get_team_owner_data activity")

        user_leagues: Dict[str, Any] = team_owner_core.get("user_leagues", {})
        # seasons from most recent to oldest
        seasons_sorted = sorted(
            user_leagues.keys(),
            key=lambda s: int(s) if isinstance(s, str) and s.isdigit() else 0,
            reverse=True,
        )

        for season in seasons_sorted:
            leagues = user_leagues.get(season, [])
            for league in leagues:
                if league.get("name") == params.league_name:
                    league_id = league.get("league_id")
                    break
            if league_id is not None:
                break
        if league_id is None:
            raise ValueError(f"No league_id found for league_name='{params.league_name}' in user_leagues")

        # Step 2: Run league-data-collection as a child workflow for this league
        league_result: Dict[str, Any] = await workflow.execute_child_workflow(
            LeagueDataCollectionWorkflow.run,
            LeagueDataCollectionWorkflowParams(league_id=league_id),
            id=f"child_workflow-league_data_collection-{_safe_slug(params.league_name)}-{league_id}-{wf_hex}",
            retry_policy=child_retry_policy,
            run_timeout=timedelta(minutes=30),
            execution_timeout=timedelta(minutes=60),
            task_timeout=timedelta(minutes=10),
        )
        child_workflow_results.append(
            {
                "workflow": "league-data-collection",
                "league_id": league_id,
                "result": league_result,
            }
        )

        return {
            "username": params.username,
            "league_name": params.league_name,
            "league_id": league_id,
            "workflow_data": child_workflow_results,
        }
