from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.league.get_data import get_league_data, GetLeagueDataParams
    from workflows.draft_data_collection import DraftDataCollectionWorkflow, DraftDataCollectionWorkflowParams

@dataclass
class LeagueDataCollectionWorkflowParams:
    """Input parameters for the league data collection workflow."""

    league_name: str

@workflow.defn(name="league-data-collection")
class LeagueDataCollectionWorkflow:
    """Workflow that collects core data for a Sleeper league."""

    @workflow.run
    async def run(self, params: LeagueDataCollectionWorkflowParams) -> Dict[str, Any]:
        """Execute the league data collection workflow."""
        workflow_activities = []
        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,  # 3 total attempts, 2 retries
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
        )

        # Get Team Owner Data Activity
        league_data = await workflow.execute_activity(
            get_league_data,
            GetLeagueDataParams(league_name=params.league_name),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_league_data-{params.league_name}",
            retry_policy=activity_retry_policy,
        )
        print(f"Get League Data Activity result: {league_data}")
        workflow_activities.append({
            "activity": "get_league_data",
            "result": league_data
        })

        # all league's seasons
        # Child workflow for draft collection
        draft_workflow_result = await workflow.execute_child_workflow(
            DraftDataCollectionWorkflow.run,
            DraftDataCollectionWorkflowParams(league_id=league_data["league_id"]),
        )
        print(f"DraftDataCollectionWorkflow result for league {league_data['league_id']}: {len(draft_workflow_result)}")
        workflow_activities.append({
            "workflow": "draft-data-collection",
            "result": draft_workflow_result,
        })


        # Return Activity Data and Workflow Output
        return {
            "activity_data": workflow_activities,
        }