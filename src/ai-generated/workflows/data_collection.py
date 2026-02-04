"""Data Collection Workflow - Orchestrates gathering historical league data from Sleeper API"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.activities.api_client import (
        fetch_user,
        fetch_user_leagues,
        fetch_league_details,
        fetch_league_rosters,
        fetch_league_users,
        fetch_league_drafts,
        fetch_draft_picks,
        fetch_players_database,
        fetch_matchups,
        fetch_transactions,
    )
    from src.activities.database import (
        store_user,
        store_leagues,
        store_drafts,
        store_picks,
        store_players,
        store_rosters,
        store_transactions,
    )


@dataclass
class DataCollectionInput:
    """Input parameters for data collection workflow"""
    username: Optional[str] = None
    user_id: Optional[str] = None
    seasons: list[str] = None  # e.g., ["2021", "2022", "2023", "2024", "2025"]
    sport: str = "nfl"
    collect_transactions: bool = True
    collect_matchups: bool = True


@dataclass
class DataCollectionResult:
    """Result of data collection workflow"""
    user_id: str
    leagues_collected: int
    drafts_collected: int
    picks_collected: int
    players_updated: int
    success: bool
    errors: list[str]


@workflow.defn
class DataCollectionWorkflow:
    """
    Main workflow for collecting historical league data from Sleeper API.
    
    This workflow:
    1. Fetches user information
    2. Retrieves all leagues for specified seasons
    3. Collects draft data and picks for each league
    4. Updates player database
    5. Optionally collects transactions and matchups
    """

    @workflow.run
    async def run(self, input_data: DataCollectionInput) -> DataCollectionResult:
        """
        Execute the data collection workflow.
        
        Args:
            input_data: Configuration for data collection
            
        Returns:
            DataCollectionResult with collection statistics
        """
        errors = []
        leagues_collected = 0
        drafts_collected = 0
        picks_collected = 0
        players_updated = 0

        try:
            # Step 1: Fetch user information
            workflow.logger.info(
                f"Starting data collection for user: {input_data.username or input_data.user_id}"
            )
            
            user_data = await workflow.execute_activity(
                fetch_user,
                input_data.username or input_data.user_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                ),
            )
            
            user_id = user_data["user_id"]
            
            # Store user in database
            await workflow.execute_activity(
                store_user,
                user_data,
                start_to_close_timeout=timedelta(seconds=10),
            )
            
            workflow.logger.info(f"User fetched: {user_id}")

            # Step 2: Fetch leagues for each season
            all_leagues = []
            for season in input_data.seasons or ["2024"]:
                leagues = await workflow.execute_activity(
                    fetch_user_leagues,
                    {"user_id": user_id, "sport": input_data.sport, "season": season},
                    start_to_close_timeout=timedelta(seconds=30),
                )
                all_leagues.extend(leagues)
                workflow.logger.info(f"Found {len(leagues)} leagues for season {season}")

            leagues_collected = len(all_leagues)

            # Store leagues in database
            if all_leagues:
                await workflow.execute_activity(
                    store_leagues,
                    all_leagues,
                    start_to_close_timeout=timedelta(seconds=30),
                )

            # Step 3: Process each league (use child workflows for parallel processing)
            for league in all_leagues:
                league_id = league["league_id"]
                
                try:
                    # Fetch league details
                    league_details = await workflow.execute_activity(
                        fetch_league_details,
                        league_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )

                    # Fetch rosters
                    rosters = await workflow.execute_activity(
                        fetch_league_rosters,
                        league_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    
                    if rosters:
                        await workflow.execute_activity(
                            store_rosters,
                            {"league_id": league_id, "rosters": rosters},
                            start_to_close_timeout=timedelta(seconds=30),
                        )

                    # Fetch league users
                    users = await workflow.execute_activity(
                        fetch_league_users,
                        league_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )

                    # Fetch drafts for this league
                    drafts = await workflow.execute_activity(
                        fetch_league_drafts,
                        league_id,
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    
                    drafts_collected += len(drafts)
                    
                    if drafts:
                        await workflow.execute_activity(
                            store_drafts,
                            drafts,
                            start_to_close_timeout=timedelta(seconds=30),
                        )

                    # Fetch picks for each draft
                    for draft in drafts:
                        draft_id = draft["draft_id"]
                        picks = await workflow.execute_activity(
                            fetch_draft_picks,
                            draft_id,
                            start_to_close_timeout=timedelta(seconds=60),
                        )
                        
                        picks_collected += len(picks)
                        
                        if picks:
                            await workflow.execute_activity(
                                store_picks,
                                picks,
                                start_to_close_timeout=timedelta(seconds=60),
                            )

                    # Optional: Fetch transactions
                    if input_data.collect_transactions:
                        # Transactions are by week/round
                        for week in range(1, 18):  # NFL regular season weeks
                            try:
                                transactions = await workflow.execute_activity(
                                    fetch_transactions,
                                    {"league_id": league_id, "round": week},
                                    start_to_close_timeout=timedelta(seconds=30),
                                )
                                
                                if transactions:
                                    await workflow.execute_activity(
                                        store_transactions,
                                        transactions,
                                        start_to_close_timeout=timedelta(seconds=30),
                                    )
                            except Exception as e:
                                workflow.logger.warning(
                                    f"Failed to fetch transactions for league {league_id} week {week}: {e}"
                                )

                    # Optional: Fetch matchups
                    if input_data.collect_matchups:
                        for week in range(1, 18):
                            try:
                                matchups = await workflow.execute_activity(
                                    fetch_matchups,
                                    {"league_id": league_id, "week": week},
                                    start_to_close_timeout=timedelta(seconds=30),
                                )
                                # TODO: Store matchups (add activity)
                            except Exception as e:
                                workflow.logger.warning(
                                    f"Failed to fetch matchups for league {league_id} week {week}: {e}"
                                )

                except Exception as e:
                    error_msg = f"Error processing league {league_id}: {str(e)}"
                    workflow.logger.error(error_msg)
                    errors.append(error_msg)

            # Step 4: Update player database (daily sync)
            try:
                players_data = await workflow.execute_activity(
                    fetch_players_database,
                    input_data.sport,
                    start_to_close_timeout=timedelta(minutes=5),  # Large response
                )
                
                await workflow.execute_activity(
                    store_players,
                    players_data,
                    start_to_close_timeout=timedelta(minutes=5),
                )
                
                players_updated = len(players_data)
                workflow.logger.info(f"Updated {players_updated} players in database")
                
            except Exception as e:
                error_msg = f"Error updating player database: {str(e)}"
                workflow.logger.error(error_msg)
                errors.append(error_msg)

            return DataCollectionResult(
                user_id=user_id,
                leagues_collected=leagues_collected,
                drafts_collected=drafts_collected,
                picks_collected=picks_collected,
                players_updated=players_updated,
                success=len(errors) == 0,
                errors=errors,
            )

        except Exception as e:
            workflow.logger.error(f"Data collection workflow failed: {str(e)}")
            return DataCollectionResult(
                user_id=input_data.user_id or "",
                leagues_collected=leagues_collected,
                drafts_collected=drafts_collected,
                picks_collected=picks_collected,
                players_updated=players_updated,
                success=False,
                errors=[str(e)],
            )

    @workflow.signal
    async def pause(self) -> None:
        """Signal to pause data collection"""
        workflow.logger.info("Pausing data collection workflow")
        # Implement pause logic if needed

    @workflow.signal
    async def resume(self) -> None:
        """Signal to resume data collection"""
        workflow.logger.info("Resuming data collection workflow")
        # Implement resume logic if needed

    @workflow.query
    def get_status(self) -> dict:
        """Query current workflow status"""
        return {
            "status": "running",
            # Add more status info as needed
        }
