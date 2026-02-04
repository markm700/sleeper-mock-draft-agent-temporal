"""Mock Draft Simulation Workflow - Monte Carlo simulation for draft prediction"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.activities.database import (
        fetch_league_settings,
        fetch_owner_profiles,
        fetch_player_pool,
    )
    from src.activities.ml_models import (
        initialize_draft_state,
        run_single_simulation,
        aggregate_simulation_results,
        generate_recommendations,
        export_results,
    )


@dataclass
class MockDraftInput:
    """Input parameters for mock draft simulation"""
    league_id: str
    season: str
    num_simulations: int = 1000
    user_overrides: Optional[dict] = None  # Force specific picks (e.g., keepers)
    export_format: str = "csv"  # csv or json


@dataclass
class MockDraftResult:
    """Result of mock draft simulation"""
    league_id: str
    simulations_completed: int
    recommendations: dict
    export_path: Optional[str]
    success: bool
    errors: list[str]


@workflow.defn
class MockDraftSimulationWorkflow:
    """
    Workflow for running mock draft simulations using Monte Carlo method.
    
    This workflow:
    1. Loads league settings and owner profiles
    2. Initializes draft state
    3. Runs multiple simulations (1000+)
    4. Aggregates results
    5. Generates recommendations (top 3 best available, top 3 best value)
    6. Exports results to CSV/JSON
    """

    @workflow.run
    async def run(self, input_data: MockDraftInput) -> MockDraftResult:
        """
        Execute the mock draft simulation workflow.
        
        Args:
            input_data: Configuration for simulation
            
        Returns:
            MockDraftResult with simulation results
        """
        errors = []
        simulations_completed = 0
        recommendations = {}
        export_path = None

        try:
            workflow.logger.info(
                f"Starting mock draft simulation for league: {input_data.league_id}"
            )
            workflow.logger.info(f"Running {input_data.num_simulations} simulations")

            # Step 1: Load league settings
            league_settings = await workflow.execute_activity(
                fetch_league_settings,
                input_data.league_id,
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Step 2: Load owner profiles
            owner_profiles = await workflow.execute_activity(
                fetch_owner_profiles,
                input_data.league_id,
                start_to_close_timeout=timedelta(seconds=60),
            )

            # Step 3: Load current player pool
            player_pool = await workflow.execute_activity(
                fetch_player_pool,
                {"season": input_data.season, "sport": "nfl"},
                start_to_close_timeout=timedelta(seconds=60),
            )

            workflow.logger.info(
                f"Loaded {len(owner_profiles)} owner profiles and {len(player_pool)} players"
            )

            # Step 4: Initialize draft state
            draft_state = await workflow.execute_activity(
                initialize_draft_state,
                {
                    "league_settings": league_settings,
                    "owner_profiles": owner_profiles,
                    "player_pool": player_pool,
                    "user_overrides": input_data.user_overrides,
                },
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Step 5: Run simulations (batch for performance)
            # Target: < 1 minute for 1000 simulations
            batch_size = 100
            all_simulation_results = []

            for batch_num in range(0, input_data.num_simulations, batch_size):
                batch_count = min(batch_size, input_data.num_simulations - batch_num)
                
                try:
                    batch_results = await workflow.execute_activity(
                        run_single_simulation,
                        {
                            "draft_state": draft_state,
                            "simulation_count": batch_count,
                        },
                        start_to_close_timeout=timedelta(seconds=120),
                    )
                    
                    all_simulation_results.extend(batch_results)
                    simulations_completed += len(batch_results)
                    
                    workflow.logger.info(
                        f"Completed {simulations_completed}/{input_data.num_simulations} simulations"
                    )
                    
                except Exception as e:
                    error_msg = f"Simulation batch {batch_num} failed: {str(e)}"
                    workflow.logger.error(error_msg)
                    errors.append(error_msg)

            # Step 6: Aggregate results
            try:
                aggregated_results = await workflow.execute_activity(
                    aggregate_simulation_results,
                    {
                        "simulation_results": all_simulation_results,
                        "player_pool": player_pool,
                    },
                    start_to_close_timeout=timedelta(seconds=60),
                )
                workflow.logger.info("Simulation results aggregated")
            except Exception as e:
                error_msg = f"Result aggregation failed: {str(e)}"
                workflow.logger.error(error_msg)
                errors.append(error_msg)
                aggregated_results = None

            # Step 7: Generate recommendations
            if aggregated_results:
                try:
                    recommendations = await workflow.execute_activity(
                        generate_recommendations,
                        {
                            "aggregated_results": aggregated_results,
                            "league_settings": league_settings,
                            "top_n": 3,  # Top 3 best available + top 3 best value
                        },
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    workflow.logger.info("Recommendations generated")
                except Exception as e:
                    error_msg = f"Recommendation generation failed: {str(e)}"
                    workflow.logger.error(error_msg)
                    errors.append(error_msg)

            # Step 8: Export results
            try:
                export_path = await workflow.execute_activity(
                    export_results,
                    {
                        "league_id": input_data.league_id,
                        "simulation_results": all_simulation_results,
                        "aggregated_results": aggregated_results,
                        "recommendations": recommendations,
                        "format": input_data.export_format,
                    },
                    start_to_close_timeout=timedelta(seconds=60),
                )
                workflow.logger.info(f"Results exported to: {export_path}")
            except Exception as e:
                error_msg = f"Export failed: {str(e)}"
                workflow.logger.error(error_msg)
                errors.append(error_msg)

            return MockDraftResult(
                league_id=input_data.league_id,
                simulations_completed=simulations_completed,
                recommendations=recommendations,
                export_path=export_path,
                success=len(errors) == 0 and simulations_completed > 0,
                errors=errors,
            )

        except Exception as e:
            workflow.logger.error(f"Mock draft simulation workflow failed: {str(e)}")
            return MockDraftResult(
                league_id=input_data.league_id,
                simulations_completed=simulations_completed,
                recommendations={},
                export_path=None,
                success=False,
                errors=[str(e)],
            )

    @workflow.signal
    async def update_overrides(self, overrides: dict) -> None:
        """Signal to update user overrides during simulation"""
        workflow.logger.info(f"Updating user overrides: {overrides}")
        # Store overrides for next simulation batch

    @workflow.query
    def get_progress(self) -> dict:
        """Query current simulation progress"""
        return {
            "status": "running",
            "simulations_completed": 0,  # Track actual progress
        }
