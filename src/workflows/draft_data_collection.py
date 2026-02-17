from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import get_league_drafts, GetLeagueDraftsParams
    from activities.draft.get_draft_picks import get_specific_draft_picks, GetSpecificDraftPicksParams

@dataclass
class DraftDataCollectionWorkflowParams:
    """Input parameters for the draft data collection workflow.

    Attributes:
        league_id: Sleeper league identifier to collect draft data for.
    """

    league_id: str

@workflow.defn(name="draft-data-collection")
class DraftDataCollectionWorkflow:
    """Workflow that collects draft and draft-pick trade data for a league."""

    @workflow.run
    async def run(self, params: DraftDataCollectionWorkflowParams) -> Dict[str, Any]:
        """Execute the draft data collection workflow.

        This workflow runs activities to fetch league drafts and specific draft
        picks (including traded picks) for the given league, and aggregates
        their results into a single response payload.
        """
        workflow_activities = []
        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,  # 3 total attempts, 2 retries
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
        )

        # Get Draft Data Activity
        draft_data = await workflow.execute_activity(
            get_league_drafts,
            GetLeagueDraftsParams(league_id=params.league_id),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_league_drafts-{params.league_id}",
            retry_policy=activity_retry_policy,
        )
        workflow.logger.info(f"Get League Drafts Activity result: {draft_data}")
        workflow_activities.append({
            "activity": "get_league_drafts",
            "result": draft_data
        })

        # Get Draft Pick Trades Data Activity
        draft_id = draft_data["league_drafts"][0]["draft_id"]
        draft_pick_trades = await workflow.execute_activity(
            get_specific_draft_picks,
            GetSpecificDraftPicksParams(draft_id=draft_id),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_specific_draft_picks-{params.league_id}-{draft_id}",
            retry_policy=activity_retry_policy,
        )
        workflow.logger.info(f"Get Specific Draft Picks Activity result: {draft_pick_trades}")
        workflow_activities.append({
            "activity": "get_specific_draft_picks",
            "result": draft_pick_trades
        })


        # Return Activity Data and Workflow Output
        return { 
            "activity_data": workflow_activities,
            "draft_data": draft_data,
            "draft_pick_trades": draft_pick_trades
        }