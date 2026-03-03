from datetime import timedelta
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.players.get_all_players import get_all_player_data

@workflow.defn(name="player-data-collection")
class PlayerDataCollectionWorkflow:
    """Workflow that collects draft and draft-pick trade data for a league."""

    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """Execute the draft data collection workflow.

        This workflow runs activities to fetch league drafts and specific draft
        picks (including traded picks) for the given league, and aggregates
        their results into a single response payload.
        """
        wf_hex = workflow.info().run_id[-4:]
        workflow_activities = []
        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,  # 3 total attempts, 2 retries
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
        )

        # Get Players Data Activity
        player_upsert_data = await workflow.execute_activity(
            get_all_player_data,
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_all_player_data-{wf_hex}",
            retry_policy=activity_retry_policy,
        )
        print(f"Get All Player Data Activity result: {player_upsert_data.get('upserted_players', 0)}/{player_upsert_data.get('total_found_players', 0)} players upserted to database")
        workflow_activities.append({
            "activity": "get_all_player_data",
            "player_database_operations": player_upsert_data
        })

        # Return Activity Data and Workflow Output
        return { 
            "activity_data": workflow_activities
        }