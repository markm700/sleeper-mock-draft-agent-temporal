from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import get_league_drafts, GetLeagueDraftsParams
    from activities.draft.get_draft_picks import get_specific_draft_picks, GetSpecificDraftPicksParams
    from activities.draft.get_traded_draft_picks import get_traded_draft_picks, GetTradedDraftPicksParams

@dataclass
class DraftDataCollectionWorkflowParams:
    """Input parameters for the draft data collection workflow.

    Attributes:
        league_id: Sleeper league identifier to collect draft data for.
        season: Season year to filter traded draft picks (defaults to 2025).
    """

    league_id: str
    season: str = "2025"

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
        print(f"Get League Drafts Activity result: {draft_data}")
        workflow_activities.append({
            "activity": "get_league_drafts",
            "draft_data": draft_data
        })

        # Get Draft Picks Data Activity
        draft_id = draft_data["league_drafts"][0]["draft_id"]
        draft_picks = await workflow.execute_activity(
            get_specific_draft_picks,
            GetSpecificDraftPicksParams(draft_id=draft_id),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_specific_draft_picks-{params.league_id}-{draft_id}",
            retry_policy=activity_retry_policy,
        )
        print(f"Specific Draft Picks Activity result: {len(draft_picks['draft_picks'])} picks for draft {draft_id}")
        workflow_activities.append({
            "activity": "get_specific_draft_picks",
            "total_draft_picks": len(draft_picks["draft_picks"]),
            "draft_picks": draft_picks
        })

        # Get Draft Pick Trade Data Activity
        draft_pick_trades = await workflow.execute_activity(
            get_traded_draft_picks,
            GetTradedDraftPicksParams(league_id=params.league_id, season=params.season),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_traded_draft_picks-{params.league_id}-{params.season}",
            retry_policy=activity_retry_policy,
        )
        print(f"Traded Draft Picks Activity result: {len(draft_pick_trades['traded_draft_picks'])} traded picks for league {params.league_id} in season {params.season}")
        workflow_activities.append({
            "activity": "get_traded_draft_picks",
            "total_traded_picks": len(draft_pick_trades["traded_draft_picks"]),
            "draft_pick_trades": draft_pick_trades
        })

        # Return Activity Data and Workflow Output
        return { 
            "activity_data": workflow_activities
        }