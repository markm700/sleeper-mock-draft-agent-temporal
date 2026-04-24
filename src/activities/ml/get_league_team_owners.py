"""
Activity to fetch all team owner user_ids for a league from PostgreSQL.

Used by LeagueModelTrainingWorkflow to discover which owners need models
trained before orchestrating per-owner training child workflows.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import TeamOwner


@dataclass
class GetLeagueTeamOwnersParams:
    """
    Parameters for fetching team owners in a league.

    Args:
        league_id: Sleeper league identifier.
        exclude_bots: Whether to exclude bot owners (default True).
    """

    league_id: str
    exclude_bots: bool = True


@activity.defn(name="get_league_team_owners")
async def get_league_team_owners(input: GetLeagueTeamOwnersParams) -> Dict[str, Any]:
    """
    Fetch all team owner user_ids for a given league.

    Args:
        input: GetLeagueTeamOwnersParams with league_id and optional bot filter.

    Returns:
        Dict[str, Any]: {
            "owner_user_ids": [str, ...],
            "num_owners": int,
            "league_id": str,
        }
    """
    postgres = get_postgres_client_manager()

    try:
        with postgres.get_session() as session:
            query = session.query(TeamOwner).filter(
                TeamOwner.league_id == input.league_id,
            )
            if input.exclude_bots:
                query = query.filter(TeamOwner.is_bot == False)

            owners = query.all()
            owner_user_ids: List[str] = [o.user_id for o in owners]

        print(
            f"Found {len(owner_user_ids)} team owners in league {input.league_id}"
        )
        return {
            "owner_user_ids": owner_user_ids,
            "num_owners": len(owner_user_ids),
            "league_id": input.league_id,
        }

    except Exception as e:
        print(f"Failed to fetch team owners for league {input.league_id}: {str(e)}")
        raise
