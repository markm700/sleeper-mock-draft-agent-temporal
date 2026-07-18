"""
Workflow to train draft prediction models for all team owners in a league.

Orchestrates a single ADP calculation shared across all owners, then launches
a ModelTrainingWorkflow child workflow for each owner. This avoids redundant
ADP computation and provides a single workflow to train all 10 (or N) models.
"""

from pydantic.dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.ml.calculate_adp import CalculateADPFromPicksParams, calculate_adp_from_picks
    from activities.ml.get_league_team_owners import (
        GetLeagueTeamOwnersParams,
        get_league_team_owners,
    )
    from workflows.model_training import ModelTrainingWorkflow, ModelTrainingWorkflowParams


@dataclass(frozen=True, kw_only=True)
class LeagueModelTrainingWorkflowParams:
    """
    Input parameters for LeagueModelTrainingWorkflow.

    Fields:
        league_id: Sleeper league_id — all owners in this league will get a model trained.
        season: Season year filter for draft picks, e.g. "2025". None includes all seasons.
        num_boost_round: Number of LightGBM boosting rounds per model (default 100).
        learning_rate: LightGBM learning rate per model (default 0.05).
        weighted_adp: Use recency-weighted ADP in feature construction (default True).
        min_picks_required: Minimum historical picks required per owner to attempt training (default 10).
        rebuild_models: If True, force-rebuild all models from scratch (default False).
        exclude_bots: Whether to exclude bot owners from training (default True).
    """

    league_id: str
    season: Optional[str] = None
    num_boost_round: int = 100
    learning_rate: float = 0.05
    weighted_adp: bool = True
    min_picks_required: int = 10
    rebuild_models: bool = False
    exclude_bots: bool = True
    additional_league_ids: Optional[List[str]] = None


@workflow.defn(name="league-model-training")
class LeagueModelTrainingWorkflow:
    """
    Train a TeamOwnerDraftModel for every team owner in a league.

    Orchestrates the following steps:

    1. **get_league_team_owners** — discover all owner user_ids in the league.
    2. **calculate_adp_from_picks** — compute per-player ADP once for the
       entire league (shared across all owner models).
    3. **ModelTrainingWorkflow (child)** — for each owner, launch a child
       workflow that prepares training data, builds the model scaffold, and
       trains the LightGBM ranker. Pre-computed ADP is passed in to avoid
       redundant calculation.

    Returns a summary with per-owner training results and overall statistics.
    """

    @workflow.run
    async def run(self, params: LeagueModelTrainingWorkflowParams) -> Dict[str, Any]:
        """
        Train models for all owners in the league.

        Args:
            params: LeagueModelTrainingWorkflowParams with league and training config.

        Returns:
            Dict[str, Any]: {
                "league_id": str,
                "num_owners": int,
                "num_trained": int,
                "num_skipped": int,
                "owner_results": [{...}, ...],
                "activity_data": [...],
            }
        """
        wf_hex = workflow.info().run_id[-4:]
        print(
            f"LeagueModelTrainingWorkflow starting — league={params.league_id} "
            f"season={params.season}"
        )

        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=2),
            backoff_coefficient=2.0,
        )
        workflow_activities: List[Dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Step 1: Discover all team owners in the league
        # ------------------------------------------------------------------
        owners_result = await workflow.execute_activity(
            get_league_team_owners,
            GetLeagueTeamOwnersParams(
                league_id=params.league_id,
                exclude_bots=params.exclude_bots,
            ),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_league_team_owners-{params.league_id}-{wf_hex}",
            retry_policy=activity_retry_policy,
        )

        owner_user_ids: List[str] = owners_result["owner_user_ids"]
        num_owners = len(owner_user_ids)
        print(f"Found {num_owners} team owners in league {params.league_id}")
        workflow_activities.append({
            "activity": "get_league_team_owners",
            "result": {"num_owners": num_owners},
        })

        if num_owners == 0:
            print("No team owners found — exiting early.")
            return {
                "league_id": params.league_id,
                "num_owners": 0,
                "num_trained": 0,
                "num_skipped": 0,
                "owner_results": [],
                "activity_data": workflow_activities,
            }

        # ------------------------------------------------------------------
        # Step 2: Calculate ADP once for the entire league
        # ------------------------------------------------------------------
        adp_result = await workflow.execute_activity(
            calculate_adp_from_picks,
            CalculateADPFromPicksParams(
                league_id=params.league_id,
                season=params.season,
                weighted=params.weighted_adp,
                additional_league_ids=params.additional_league_ids,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            activity_id=(
                f"activity-calculate_adp-{params.league_id}"
                f"-{params.season or 'all'}-{wf_hex}"
            ),
            retry_policy=activity_retry_policy,
        )
        print(
            f"ADP calculated: {adp_result['num_players']} players across "
            f"{adp_result['num_drafts']} drafts ({adp_result['num_picks']} picks)"
        )
        workflow_activities.append({
            "activity": "calculate_adp_from_picks",
            "result": {
                "num_players": adp_result["num_players"],
                "num_picks": adp_result["num_picks"],
                "num_drafts": adp_result["num_drafts"],
            },
        })

        # ------------------------------------------------------------------
        # Step 3: Train each owner's model via child workflows
        # ------------------------------------------------------------------
        owner_results: List[Dict[str, Any]] = []
        num_trained = 0
        num_skipped = 0

        for idx, user_id in enumerate(owner_user_ids):
            model_name = f"owner_{user_id}_{params.league_id}_v1"
            print(
                f"Training model {idx + 1}/{num_owners}: "
                f"user={user_id} model={model_name}"
            )

            child_result = await workflow.execute_child_workflow(
                ModelTrainingWorkflow.run,
                ModelTrainingWorkflowParams(
                    league_id=params.league_id,
                    user_id=user_id,
                    model_name=model_name,
                    season=params.season,
                    num_boost_round=params.num_boost_round,
                    learning_rate=params.learning_rate,
                    weighted_adp=params.weighted_adp,
                    min_picks_required=params.min_picks_required,
                    rebuild_model=params.rebuild_models,
                    precomputed_adp_data=adp_result,
                    additional_league_ids=params.additional_league_ids,
                ),
                id=(
                    f"child-model-training-{user_id}"
                    f"-{params.league_id}-{wf_hex}"
                ),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=10),
                    maximum_interval=timedelta(minutes=5),
                    backoff_coefficient=2.0,
                ),
            )

            skipped = child_result.get("skipped", False)
            if skipped:
                num_skipped += 1
            else:
                num_trained += 1

            owner_results.append({
                "user_id": user_id,
                "model_name": model_name,
                "skipped": skipped,
                "num_boost_round": child_result.get("num_boost_round", 0),
                "num_samples": child_result.get("num_samples", 0),
                "num_query_groups": child_result.get("num_query_groups", 0),
                "model_path": child_result.get("model_path", ""),
            })

            print(
                f"Owner {idx + 1}/{num_owners} done: "
                f"user={user_id} skipped={skipped} "
                f"samples={child_result.get('num_samples', 0)}"
            )

        print(
            f"LeagueModelTrainingWorkflow complete — "
            f"trained={num_trained}, skipped={num_skipped}, total={num_owners}"
        )

        return {
            "league_id": params.league_id,
            "season": params.season,
            "num_owners": num_owners,
            "num_trained": num_trained,
            "num_skipped": num_skipped,
            "owner_results": owner_results,
            "activity_data": workflow_activities,
        }
