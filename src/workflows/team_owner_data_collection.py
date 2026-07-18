from datetime import timedelta
from pydantic.dataclasses import dataclass
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.team_owner.get_data import get_team_owner_data, GetTeamOwnerDataParams
    from activities.team_owner.get_roster import get_team_owner_rosters, GetLeagueRosterParams

@dataclass(frozen=True, kw_only=True)
class TeamOwnerDataCollectionWorkflowParams:
    """
    Input parameters for the team owner data collection workflow.

    Fields:
        username: Sleeper username for the team owner.
        league_name: Human-readable league name used to filter leagues.
    """

    username: str
    league_name: str

@workflow.defn(name="team-owner-data-collection")
class TeamOwnerDataCollectionWorkflow:
    """Workflow that collects team owner and roster data across seasons."""

    @workflow.run
    async def run(self, params: TeamOwnerDataCollectionWorkflowParams) -> Dict[str, Any]:
        """
        Execute the team owner data collection workflow.

        Fetches team owner data and iterates over all their leagues to collect
        roster data for each season.

        Args:
            params: TeamOwnerDataCollectionWorkflowParams with username and league_name.

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

        # Get Team Owner Data Activity
        team_owner_data = await workflow.execute_activity(
            get_team_owner_data,
            GetTeamOwnerDataParams(username=params.username, league_name=params.league_name),
            start_to_close_timeout=timedelta(seconds=10),
            activity_id=f"activity-get_team_owner_data-{params.username}-{params.league_name}-{wf_hex}",
            retry_policy=activity_retry_policy,
        )
        print(f"Get Team Owner Data Activity result: {team_owner_data['user_id'] if team_owner_data else 'No Team Owner found'}")
        workflow_activities.append({
            "activity": "get_team_owner_data",
            "result": team_owner_data
        })

        # all league's seasons -> get roster for league season -> filter for team owner roster
        # team_owner_data["user_leagues"] is a mapping of season -> list of league dicts
        owner_league_rosters = []
        for season, leagues in team_owner_data["user_leagues"].items():
            for league in leagues:
                league_id = league.get("league_id")
                if not league_id:
                    continue

                # Get Team Owner Roster Activity for this league
                team_owner_roster = await workflow.execute_activity(
                    get_team_owner_rosters,
                    GetLeagueRosterParams(league_id=league_id, user_id=team_owner_data["user_id"]),
                    start_to_close_timeout=timedelta(seconds=10),
                    activity_id=(
                        f"activity-get_team_owner_rosters-{params.username}-{params.league_name}-{season}_season-{wf_hex}"
                    ),
                    retry_policy=activity_retry_policy,
                )
                print(
                    f"Get Team Owner {params.username} Roster Activity for league {league_id} {season} season: {team_owner_roster.get('roster')[0]['roster_id'] if team_owner_roster.get('roster') else 'No roster found'}"
                )
                owner_league_rosters.append({
                    "season": season,
                    "league_id": league_id,
                    "result": team_owner_roster,
                })
        workflow_activities.append({
            "activity": "get_team_owner_rosters",
            "user_rosters": owner_league_rosters,
        })

        # Return Activity Data and Workflow Output
        return { 
            "activity_data": workflow_activities
        }