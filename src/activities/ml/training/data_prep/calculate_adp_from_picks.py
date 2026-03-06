"""ML training data preparation activities using PostgreSQL data."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from sqlalchemy import select, func
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import DraftPick, Draft

@dataclass
class CalculateADPParams:
    """Parameters for calculating Average Draft Position."""
    league_ids: Optional[List[str]] = None  # Filter by specific leagues, None = all
    season: Optional[str] = None            # Filter by season, None = all
    min_picks: int = 3                      # Minimum picks for a player to be included


@activity.defn(name="calculate_adp_from_picks")
async def calculate_adp_from_picks(input: CalculateADPParams) -> Dict[str, Any]:
    """
    Calculate Average Draft Position (ADP) from historical draft picks in PostgreSQL.
    
    Analyzes all completed drafts to compute comprehensive ADP statistics for each player.
    ADP metrics help identify consensus player value and draft trends across multiple drafts.
    
    Calculated Metrics:
    - Mean ADP: Average pick position across all drafts (lower = earlier/more valuable)
    - Std Dev: Draft volatility (higher = less consensus on value)
    - Min/Max: Earliest and latest picks (shows value range)
    - Times Drafted: Frequency picked (shows popularity/availability)
    
    Use Cases:
    - Training data preparation: Normalize player value for ML features
    - Draft strategy: Identify value picks and reaches
    - Owner analysis: Compare owner picks vs ADP (reach vs value drafting)
    
    Args:
        input: CalculateADPParams containing:
            - league_ids: Optional list of league IDs to filter (None = all leagues)
            - season: Optional season filter (e.g., "2023", None = all seasons)
            - min_picks: Minimum times drafted to include player (default: 3)
    
    Returns:
        Dict[str, Any] with structure:
        {
            "adp_data": {
                "<player_id>": {
                    "avg_pick": float,      # Mean pick position
                    "std_pick": float,      # Pick position std deviation
                    "num_picks": int,       # Times drafted
                    "min_pick": int,        # Earliest pick
                    "max_pick": int         # Latest pick
                }
            },
            "total_players": int,       # Unique players with ADP data
            "total_picks_analyzed": int # Total draft picks analyzed
        }
    
    Example:
        # Calculate ADP for all historical drafts
        result = await calculate_adp_from_picks(
            CalculateADPParams(min_picks=5)  # Only players picked 5+ times
        )
        # Access specific player ADP
        rb_adp = result["adp_data"]["8150"]["avg_pick"]  # Christian McCaffrey
    
    Performance:
        - ~500ms-2s for 10+ drafts (depends on league size)
        - Scales with: draft_count * picks_per_draft
    
    Related Activities:
        - enrich_training_samples: Uses ADP as ML feature
        - analyze_owner_preferences: Compares picks vs ADP for reach analysis
    """
    try:
        postgres = get_postgres_client_manager()
        
        with postgres.get_session() as session:
            # Build query for draft picks
            query = (
                select(
                    DraftPick.player_id,
                    func.avg(DraftPick.pick_no).label('avg_pick'),
                    func.stddev(DraftPick.pick_no).label('std_pick'),
                    func.count(DraftPick.pick_id).label('num_picks'),
                    func.min(DraftPick.pick_no).label('min_pick'),
                    func.max(DraftPick.pick_no).label('max_pick'),
                )
                .join(Draft, DraftPick.draft_id == Draft.draft_id)
                .where(DraftPick.player_id.isnot(None))
                .group_by(DraftPick.player_id)
                .having(func.count(DraftPick.pick_id) >= input.min_picks)
            )
            
            # Apply filters
            if input.league_ids:
                query = query.where(Draft.league_id.in_(input.league_ids))
            if input.season:
                query = query.where(Draft.season == input.season)
            
            results = session.execute(query).all()
            
            # Build ADP dictionary
            adp_data = {}
            for row in results:
                adp_data[row.player_id] = {
                    "player_id": row.player_id,
                    "adp": float(row.avg_pick) if row.avg_pick else 999.0,
                    "std_dev": float(row.std_pick) if row.std_pick else 0.0,
                    "times_drafted": int(row.num_picks),
                    "min_pick": int(row.min_pick),
                    "max_pick": int(row.max_pick),
                }
        
        print(f"Calculated ADP for {len(adp_data)} players")
        
        return {
            "adp_data": adp_data,
            "total_players": len(adp_data),
            "filters": {
                "leagues": input.league_ids,
                "season": input.season,
                "min_picks": input.min_picks
            }
        }
        
    except Exception as e:
        print(f"Failed to calculate ADP: {str(e)}")
        raise


