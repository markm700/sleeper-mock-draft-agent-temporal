from asyncio import gather
from datetime import timedelta
from pydantic.dataclasses import dataclass
from typing import Any, Dict, Optional
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.team_owner_data_collection import TeamOwnerDataCollectionWorkflow, TeamOwnerDataCollectionWorkflowParams
    from workflows.league_data_collection import LeagueDataCollectionWorkflow, LeagueDataCollectionWorkflowParams
    from workflows.player_data_collection import PlayerDataCollectionWorkflow

def _safe_slug(text: str | None) -> str:
    """
    Build a safe slug from text for use in workflow IDs.

    Args:
        text: Input string to slugify. None returns "value".

    Returns:
        str: Lowercase alphanumeric slug with underscores, e.g. "my_league_2025".
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

@dataclass(frozen=True, kw_only=True)
class FullDataCollectionWorkflowParams:
    """
    Input parameters for the full data collection workflow.

    Fields:
        username: Sleeper username for the team owner.
        league_name: Human-readable league name used to filter leagues.
    """

    username: str
    league_name: str


@workflow.defn(name="full-data-collection")
class FullDataCollectionWorkflow:
    """
    Workflow that chains team-owner, league, and player data collection.

    Resolves the league_id for the given username and league_name, then runs
    team-owner-data-collection, league-data-collection, and player-data-collection
    as sequential child workflows.
    """

    @workflow.run
    async def run(self, params: FullDataCollectionWorkflowParams) -> Dict[str, Any]:
        """
        Execute the full data collection workflow.

        Chains three child workflows: team-owner, league, and player data collection.
        Resolves the target league_id by matching league_name in the owner's leagues.

        Args:
            params: FullDataCollectionWorkflowParams with username and league_name.

        Returns:
            Dict[str, Any]: {
                "username": str,
                "league_name": str,
                "league_id": str,
                "workflow_data": [...],
            }
        """
        wf_hex = workflow.info().run_id[-4:]
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

        # Collect ALL league_ids for the matching league name across all seasons
        all_league_ids: list[str] = []
        for season in seasons_sorted:
            leagues = user_leagues.get(season, [])
            for league in leagues:
                if league.get("name") == params.league_name:
                    all_league_ids.append(league.get("league_id"))

        if not all_league_ids:
            raise ValueError(f"No league_id found for league_name='{params.league_name}' in user_leagues")

        # Use the most recent league_id as the primary
        league_id = all_league_ids[0]
        workflow.logger.info(
            f"Found {len(all_league_ids)} seasons for '{params.league_name}': "
            f"{all_league_ids}"
        )

        # Step 2: Run league-data-collection for ALL seasons of this league
        league_season_wf_handlers = [
            workflow.execute_child_workflow(
                LeagueDataCollectionWorkflow.run,
                LeagueDataCollectionWorkflowParams(league_id=lid),
                id=f"child_workflow-league_data_collection-{_safe_slug(params.league_name)}-{idx}-{lid}-{wf_hex}",
                retry_policy=child_retry_policy,
                run_timeout=timedelta(minutes=30),
                execution_timeout=timedelta(minutes=60),
                task_timeout=timedelta(minutes=10),
            ) for idx, lid in enumerate(all_league_ids)
        ]
        # Step 3: Run player-data-collection as a child workflow for this league
        player_data_collection_wf = workflow.execute_child_workflow(
            PlayerDataCollectionWorkflow.run,
            id=f"child_workflow-player_data_collection-{wf_hex}",
            retry_policy=child_retry_policy,
            run_timeout=timedelta(minutes=30),
            execution_timeout=timedelta(minutes=60),
            task_timeout=timedelta(minutes=10),
        )
        # Step 2 and 3 workflows in parallel, idependent of each other
        *league_season_results, players_result = await gather(*league_season_wf_handlers, player_data_collection_wf)

        child_workflow_results.append(
            {
                "workflow": "league-data-collection",
                "leagues_processed": len(league_season_results),
                "result": league_season_results,
            }
        )
        child_workflow_results.append(
            {
                "workflow": "player-data-collection",
                "result": players_result,
            }
        )

        return {
            "username": params.username,
            "league_name": params.league_name,
            "league_id": league_id,
            "all_league_ids": all_league_ids,
            "workflow_data": child_workflow_results,
        }
