import os
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

    league_id: str

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
        child_workflow_retry_policy = RetryPolicy(
            maximum_attempts=3,  # 3 total attempts, 2 retries
            initial_interval=timedelta(minutes=5),
            maximum_interval=timedelta(minutes=10),
            backoff_coefficient=2.0,
        )

        # Get Team Owner Data Activity
        league_info = await workflow.execute_activity(
            get_league_data,
            GetLeagueDataParams(league_id=params.league_id),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_league_data-{params.league_id}",
            retry_policy=activity_retry_policy,
        )
        print(f"League Data Activity result: Total Users {len(league_info['league_users'])}, Total Teams {len(league_info['league_rosters'])}")
        workflow_activities.append({
            "activity": "get_league_data",
            "result": league_info
        })

        # Child workflow for draft collection
        season = league_info["league_data"]["season"]
        draft_workflow_result = await workflow.execute_child_workflow(
            DraftDataCollectionWorkflow.run,
            DraftDataCollectionWorkflowParams(league_id=params.league_id,season=season),
            id=f"child_workflow-draft_data_collection-{params.league_id}-{season}-{os.urandom(4).hex()}",
            retry_policy=child_workflow_retry_policy,
            run_timeout=timedelta(minutes=30),
            execution_timeout=timedelta(minutes=60),
            task_timeout=timedelta(minutes=10)
        )
        print(f"DraftDataCollectionWorkflow result for league {params.league_id}, {season} season: {len(draft_workflow_result)}")
        workflow_activities.append({
            "workflow": "draft-data-collection",
            "result": draft_workflow_result,
        })


        # Return Activity Data and Workflow Output
        return {
            "activity_data": workflow_activities
        }