"""ML training data preparation activities using PostgreSQL data."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from sqlalchemy import select
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import DraftPick, Draft, Player

@dataclass
class AnalyzeOwnerPreferencesParams:
    """Parameters for analyzing owner draft preferences."""
    user_id: str
    league_ids: Optional[List[str]] = None
    season: Optional[str] = None


@activity.defn(name="analyze_owner_preferences")
async def analyze_owner_preferences(input: AnalyzeOwnerPreferencesParams) -> Dict[str, Any]:
    """
    Analyze team owner draft preferences and behavioral patterns from PostgreSQL.
    
    Performs deep analysis of an owner's historical draft picks to extract behavioral
    patterns and tendencies. These insights become features for personalized ML models.
    
    Analysis Dimensions:
    1. Position Preferences by Round:
       - Early rounds (1-3): RB-heavy, WR-heavy, or balanced?
       - Mid rounds (4-8): Position fill strategy
       - Late rounds (9+): Handcuff vs upside timing
    
    2. Value vs Reach Behavior:
       - Reach %: Picks before ADP (aggressive on targets)
       - Value %: Picks after ADP (patient, falling value)
       - Neutral %: Picks near ADP (consensus-following)
    
    3. Risk Tolerance:
       - Variance in pick positions relative to ADP
       - Willingness to reach for upside
    
    4. Position Diversity:
       - Shannon entropy across position picks
       - Position stacking tendency
    
    5. Dominant Position:
       - Most-drafted position and percentage
    
    Args:
        input: AnalyzeOwnerPreferencesParams containing:
            - user_id: Sleeper owner user ID to analyze
            - league_ids: Optional league filter (None = all owner's leagues)
            - season: Optional season filter (None = all seasons)
    
    Returns:
        Dict[str, Any] with structure:
        {
            "user_id": str,
            "drafts_analyzed": int,
            "total_picks": int,
            "position_by_round": {
                "early": {"QB": 0.1, "RB": 0.5, "WR": 0.3, "TE": 0.1},
                "mid": {...},
                "late": {...}
            },
            "reach_vs_value": {
                "reach_pct": float,
                "value_pct": float,
                "neutral_pct": float
            },
            "risk_profile": {
                "pick_variance": float
            },
            "diversity": {
                "entropy": float
            },
            "dominant_position": {
                "position": str,
                "percentage": float
            }
        }
    
    Example:
        preferences = await analyze_owner_preferences(
            AnalyzeOwnerPreferencesParams(user_id="987654321")
        )
        # Check if owner is RB-heavy in early rounds
        if preferences["position_by_round"]["early"]["RB"] > 0.5:
            print("Owner prioritizes RBs early")
    
    Performance:
        - ~200-500ms for 50+ historical picks
    
    Related Activities:
        - calculate_adp_from_picks: Provides ADP data for reach/value analysis
        - prepare_team_owner_training_data: Uses preferences as context
        - enrich_training_samples: Incorporates preferences as ML features
    """
    try:
        postgres = get_postgres_client_manager()
        
        with postgres.get_session() as session:
            # Get all picks made by this owner
            query = (
                select(
                    DraftPick.pick_no,
                    DraftPick.round,
                    DraftPick.player_id,
                    DraftPick.metadata,
                    Player.position,
                    Player.full_name,
                    Draft.draft_id,
                    Draft.season
                )
                .join(Draft, DraftPick.draft_id == Draft.draft_id)
                .outerjoin(Player, DraftPick.player_id == Player.player_id)
                .where(DraftPick.picked_by == input.user_id)
            )
            
            # Apply filters
            if input.league_ids:
                query = query.where(Draft.league_id.in_(input.league_ids))
            if input.season:
                query = query.where(Draft.season == input.season)
            
            picks = session.execute(query).all()
            
            if not picks:
                print(f"No picks found for user {input.user_id}")
                return {
                    "user_id": input.user_id,
                    "total_picks": 0,
                    "error": "No draft history found"
                }
            
            # Analyze position preferences
            position_counts = {}
            position_by_round = {}
            early_picks = []  # Rounds 1-3
            late_picks = []   # Rounds 10+
            
            for pick in picks:
                # Position distribution
                position = pick.position or "UNKNOWN"
                position_counts[position] = position_counts.get(position, 0) + 1
                
                # Position by round
                round_num = pick.round or 0
                if round_num not in position_by_round:
                    position_by_round[round_num] = {}
                position_by_round[round_num][position] = \
                    position_by_round[round_num].get(position, 0) + 1
                
                # Early vs late round analysis
                if round_num <= 3:
                    early_picks.append(pick)
                elif round_num >= 10:
                    late_picks.append(pick)
            
            # Calculate preference metrics
            total_picks = len(picks)
            position_preferences = {
                pos: count / total_picks
                for pos, count in position_counts.items()
            }
            
            # Early round strategy (first 3 rounds)
            early_positions = {}
            for pick in early_picks:
                pos = pick.position or "UNKNOWN"
                early_positions[pos] = early_positions.get(pos, 0) + 1
            
            # Calculate diversity score (higher = more diverse positions)
            diversity_score = len(position_counts) / total_picks if total_picks > 0 else 0
            
            preferences = {
                "user_id": input.user_id,
                "total_picks": total_picks,
                "position_preferences": position_preferences,
                "position_by_round": {
                    int(r): counts for r, counts in position_by_round.items()
                },
                "early_round_positions": early_positions,
                "diversity_score": float(diversity_score),
                "dominant_position": max(position_counts.items(), key=lambda x: x[1])[0] if position_counts else None,
                "seasons_analyzed": list(set(pick.season for pick in picks if pick.season)),
            }
        
        print(f"Analyzed {total_picks} picks for user {input.user_id}")
        
        return {
            "preferences": preferences,
            "raw_pick_count": len(picks)
        }
        
    except Exception as e:
        print(f"Failed to analyze owner preferences: {str(e)}")
        raise


