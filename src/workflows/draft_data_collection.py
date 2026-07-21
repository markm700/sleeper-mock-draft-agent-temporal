from asyncio import gather
from datetime import timedelta
from pydantic.dataclasses import dataclass
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import get_league_drafts, GetLeagueDraftsParams
    from activities.draft.get_draft_picks import get_specific_draft_picks, GetSpecificDraftPicksParams
    from activities.draft.get_traded_draft_picks import get_traded_draft_picks, GetTradedDraftPicksParams

@dataclass(frozen=True, kw_only=True)
class DraftDataCollectionWorkflowParams:
    """
    Input parameters for the draft data collection workflow.

    Fields:
        league_id: Sleeper league identifier to collect draft data for.
        season: Season year to filter traded draft picks (default "2025").
    """

    league_id: str
    season: str = "2025"

@workflow.defn(name="draft-data-collection")
class DraftDataCollectionWorkflow:
    """Workflow that collects draft and draft-pick trade data for a league."""

    @workflow.run
    async def run(self, params: DraftDataCollectionWorkflowParams) -> Dict[str, Any]:
        """
        Execute the draft data collection workflow.

        Fetches league drafts, specific draft picks, and traded draft picks
        for the given league and aggregates results into a single payload.

        Args:
            params: DraftDataCollectionWorkflowParams with league_id and season.

        Returns:
            Dict[str, Any]: {"activity_data": [{"activity": str, ...}, ...]}
        """
        wf_hex = workflow.info().run_id[-4:]
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
            activity_id=f"activity-get_league_drafts-{params.league_id}-{wf_hex}",
            retry_policy=activity_retry_policy,
        )
        workflow.logger.info(f"Get League Drafts Activity result: {len(draft_data['league_drafts'])} drafts for league {params.league_id}")
        workflow_activities.append({
            "activity": "get_league_drafts",
            "draft_data": draft_data
        })

        # 1 draft-picks activity and traded-picks activity per draft (parameter dependent)
        # Execute in parallel
        draft_pick_handler = [
            workflow.execute_activity(
                get_specific_draft_picks,
                GetSpecificDraftPicksParams(draft_id=draft["draft_id"]),
                start_to_close_timeout=timedelta(seconds=30),
                activity_id=f"activity-get_specific_draft_picks-{params.league_id}-{draft['draft_id']}-{wf_hex}",
                retry_policy=activity_retry_policy,
            ) for draft in draft_data["league_drafts"]
        ]

        # Await all draft-picks activities and traded-picks activity together.
        *draft_pick_results, draft_pick_trades = await gather(
            *draft_pick_handler, 
            workflow.execute_activity(
                get_traded_draft_picks,
                GetTradedDraftPicksParams(league_id=params.league_id, season=params.season),
                start_to_close_timeout=timedelta(seconds=30),
                activity_id=f"activity-get_traded_draft_picks-{params.league_id}-{params.season}-{wf_hex}",
                retry_policy=activity_retry_policy,
            )
        )
        workflow.logger.info(f"Successfully collected draft picks for all drafts in the league: {len(draft_pick_results)} drafts processed")
        workflow.logger.info(f"Draft Pick Activity results: {[len(result.get('draft_picks', [])) for result in draft_pick_results]} picks per draft")
        
        # Draft Metric Data
        total_picks_collected = 0
        for draft_picks in draft_pick_results:
            draft_id = draft_picks.get("draft_id")
            num_picks = len(draft_picks.get("draft_picks", []))
            total_picks_collected += num_picks
            workflow.logger.info(f"Specific Draft Picks Activity result: {num_picks} picks for draft {draft_id}")
            workflow_activities.append({
                "activity": "get_specific_draft_picks",
                "draft_id": draft_id,
                "total_draft_picks": num_picks,
                "draft_picks": draft_picks
            })

        workflow.logger.info(f"Total draft picks collected: {total_picks_collected} across {len(draft_data['league_drafts'])} drafts")

        # Process the concurrently-collected traded draft picks
        workflow.logger.info(f"Traded Draft Picks Activity result: {len(draft_pick_trades.get('traded_draft_picks', []))} traded picks for league {params.league_id} in season {params.season}")
        workflow_activities.append({
            "activity": "get_traded_draft_picks",
            "total_traded_picks": len(draft_pick_trades.get("traded_draft_picks", [])),
            "draft_pick_trades": draft_pick_trades
        })

        # Return Activity Data and Workflow Output
        return { 
            "activity_data": workflow_activities
        }