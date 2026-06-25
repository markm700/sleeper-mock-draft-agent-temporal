"""
Activity to prepare training samples for team owner draft prediction models.

Queries DraftPick, Draft, Player, and TeamOwner records from PostgreSQL to
construct per-pick training samples and compute the owner's historical draft
behaviour profile vector (OWNER_PROFILE_FEATURES).

Each training sample contains:
  - The picked player's encoded feature vector (target; always index 0)
  - Up to MAX_NEGATIVES encoded feature vectors for players drafted later
    in the same draft (negatives; the owner passed on these players)
  - An 8-dimensional draft-context vector at the time of the pick
  - The overall pick number and round for debugging / filtering

The output is structured for direct consumption by train_team_owner_model.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.postgres_client import get_postgres_client_manager
    from activities.ml.models.team_owner_model import OWNER_PROFILE_DIM
    from schema.constants import get_random_personality_trait
    from schema.database_models import Draft, DraftPick, Player, TeamOwner, User


# Maximum number of negative examples to include per training sample.
MAX_NEGATIVES: int = 9  # 1 positive + 9 negatives = 10-way classification per pick

_POSITION_MAP: Dict[str, int] = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}
_STATUS_MAP: Dict[str, float] = {
    "Active": 1.0, "Inactive": 0.0, "Reserve": 0.5, "PUP": 0.3, "Suspended": 0.2,
}

# Standard roster slot sizes used for context normalisation
_RB_SLOTS = 4.0
_WR_SLOTS = 5.0
_QB_SLOTS = 3.0
_TE_SLOTS = 3.0
_ROUND_NORM = 18.0
_PICK_NORM = 200.0


@dataclass
class PrepareOwnerTrainingDataParams:
    """
    Parameters for preparing training data for a single team owner's model.

    Fields:
        league_id: Primary Sleeper league identifier.
        user_id: Sleeper user identifier of the team owner.
        season: Season year filter, e.g. "2025". None includes all seasons.
        adp_data: Pre-computed ADP dict from calculate_adp_from_picks. None triggers a default.
        min_picks_required: Minimum historical picks needed before training proceeds.
        additional_league_ids: Extra league_ids (prior seasons) to include in training data.
    """

    league_id: str
    user_id: str
    season: Optional[str] = None  # e.g. "2025"; None = include all seasons
    adp_data: Optional[Dict[str, Any]] = None  # from calculate_adp_from_picks["adp_data"]
    min_picks_required: int = 10
    additional_league_ids: Optional[List[str]] = None


@activity.defn(name="prepare_owner_training_data")
async def prepare_owner_training_data(
    input: PrepareOwnerTrainingDataParams,
) -> Dict[str, Any]:
    """
    Prepare encoded training samples and the owner profile for model training.

    Fetches DraftPick, Draft, Player, and TeamOwner records, reconstructs draft
    context at each pick, encodes player features, and computes the 26-dim owner
    profile vector.

    Args:
        input: PrepareOwnerTrainingDataParams with league_id, user_id, optional season,
            optional ADP data, and minimum-picks threshold.

    Returns:
        Dict[str, Any]: {
            "training_samples": [{"pick_no": int, "round": int, "candidate_features": [...], ...}],
            "owner_profile": [float, ...],
            "num_samples": int,
            "user_id": str,
            "league_id": str,
            "season": str | None,
        }
    """
    postgres = get_postgres_client_manager()

    try:
        with postgres.session_scope() as session:
            # Build the set of league_ids to query across (primary + additional)
            all_league_ids = [input.league_id]
            if input.additional_league_ids:
                all_league_ids.extend(input.additional_league_ids)

            # Resolve team owner to confirm membership in at least one of these leagues
            team_owner = (
                session.query(TeamOwner)
                .filter(
                    TeamOwner.user_id == input.user_id,
                    TeamOwner.league_id.in_(all_league_ids),
                )
                .first()
            )
            if team_owner is None:
                raise ValueError(
                    f"TeamOwner not found: user_id={input.user_id} "
                    f"league_ids={all_league_ids}"
                )

            # Resolve personality trait: TeamOwner → User → random fallback
            personality_trait = team_owner.personality_trait
            if not personality_trait:
                user = session.query(User).filter(User.user_id == input.user_id).first()
                personality_trait = (user.personality_trait if user and user.personality_trait
                                     else get_random_personality_trait())

            # Fetch drafts across all league_ids, optionally filtered by season
            draft_query = session.query(Draft).filter(Draft.league_id.in_(all_league_ids))
            if input.season:
                draft_query = draft_query.filter(Draft.season == input.season)
            drafts = draft_query.all()

            if not drafts:
                print(
                    f"No drafts found for league {input.league_id} "
                    f"season={input.season}"
                )
                return _empty_result(input)

            draft_ids = [d.draft_id for d in drafts]

            # Fetch all picks across these drafts, ordered for chronological reconstruction
            all_picks: List[DraftPick] = (
                session.query(DraftPick)
                .filter(DraftPick.draft_id.in_(draft_ids))
                .order_by(DraftPick.draft_id, DraftPick.pick_no)
                .all()
            )

            # Partition picks by draft for context reconstruction
            picks_by_draft: Dict[str, List[DraftPick]] = defaultdict(list)
            for pick in all_picks:
                picks_by_draft[pick.draft_id].append(pick)

            # Isolate this owner's picks
            owner_picks = [p for p in all_picks if p.picked_by == input.user_id]

            if len(owner_picks) < input.min_picks_required:
                print(
                    f"Insufficient picks for user {input.user_id}: "
                    f"{len(owner_picks)} < {input.min_picks_required} required"
                )
                return _empty_result(input)

            # Bulk-load player data for all players encountered across these drafts
            all_player_ids = list({p.player_id for p in all_picks if p.player_id})
            players_map: Dict[str, Player] = {}
            if all_player_ids:
                from sqlalchemy import select as sa_select

                rows = session.execute(
                    sa_select(Player).where(Player.player_id.in_(all_player_ids))
                ).scalars().all()
                players_map = {p.player_id: p for p in rows}

            adp_data = input.adp_data or {}

            # Build one training sample per owner pick
            training_samples: List[Dict[str, Any]] = []
            for pick in owner_picks:
                if not pick.player_id:
                    continue

                draft_picks_in_this_draft = picks_by_draft[pick.draft_id]

                # Owner's roster immediately before this pick (for context)
                roster_before: Dict[str, int] = defaultdict(int)
                for prev in draft_picks_in_this_draft:
                    if (
                        prev.picked_by == input.user_id
                        and prev.pick_no < pick.pick_no
                        and prev.player_id
                    ):
                        player = players_map.get(prev.player_id)
                        if player and player.position:
                            roster_before[player.position] += 1

                # Total picks in this draft (for picks_remaining calculation)
                total_picks_in_draft = len(draft_picks_in_this_draft)

                # Positive: encode the picked player
                picked_player = players_map.get(pick.player_id)
                adp_info = adp_data.get(pick.player_id, {})
                positive_features = _encode_player(picked_player, adp_info)

                # Negatives: players drafted by others after this pick in the same draft
                negatives_raw = [
                    p for p in draft_picks_in_this_draft
                    if p.pick_no > pick.pick_no
                    and p.picked_by != input.user_id
                    and p.player_id
                ][:MAX_NEGATIVES]

                negative_features = [
                    _encode_player(players_map.get(neg.player_id), adp_data.get(neg.player_id, {}))
                    for neg in negatives_raw
                ]

                # Pad to MAX_NEGATIVES with default zero-vectors if fewer available
                while len(negative_features) < MAX_NEGATIVES:
                    negative_features.append(_default_player_features())

                # Context vector at pick time
                context = _build_context(
                    pick=pick,
                    roster_before=dict(roster_before),
                    total_picks=total_picks_in_draft,
                )

                training_samples.append(
                    {
                        "pick_no": pick.pick_no,
                        "round": pick.round,
                        "candidate_features": [positive_features] + negative_features,
                        "context": context,
                        "target_idx": 0,  # positive is always first
                        "draft_id": pick.draft_id,
                    }
                )

            # Compute 26-dim owner profile from all historical picks
            owner_profile = _compute_owner_profile(owner_picks, players_map, adp_data)

            print(
                f"Prepared {len(training_samples)} training samples "
                f"for user {input.user_id} in league {input.league_id}"
            )
            return {
                "training_samples": training_samples,
                "owner_profile": owner_profile,
                "personality_trait": personality_trait,
                "num_samples": len(training_samples),
                "user_id": input.user_id,
                "league_id": input.league_id,
                "season": input.season,
            }

    except Exception as e:
        print(
            f"Failed to prepare training data for user {input.user_id} "
            f"in league {input.league_id}: {str(e)}"
        )
        raise


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _empty_result(input: PrepareOwnerTrainingDataParams) -> Dict[str, Any]:
    """
    Return an empty result payload for use when training data is unavailable.

    Args:
        input: PrepareOwnerTrainingDataParams used to populate the returned identifiers.

    Returns:
        Dict[str, Any]: Empty training_samples and zero-filled owner_profile.
    """
    return {
        "training_samples": [],
        "owner_profile": [0.0] * OWNER_PROFILE_DIM,
        "personality_trait": get_random_personality_trait(),
        "num_samples": 0,
        "user_id": input.user_id,
        "league_id": input.league_id,
        "season": input.season,
    }


def _encode_player(player: Optional[Any], adp_info: Dict[str, Any]) -> List[float]:
    """
    Encode a Player ORM object and ADP info into the 9-dim feature vector.

    Args:
        player: Player ORM row. None returns a zero-filled default vector.
        adp_info: ADP metrics dict for this player from calculate_adp_from_picks.

    Returns:
        List[float]: 9-dim vector [position, status, age, exp, adp_inv, pts, rank_inv, has_team, is_injured].
    """
    if player is None:
        return _default_player_features()

    pos_idx = float(_POSITION_MAP.get(player.position or "", -1))
    status_enc = _STATUS_MAP.get(player.status or "Active", 0.5)
    adp = adp_info.get("adp", 999.0)

    return [
        pos_idx,
        status_enc,
        (player.age or 0) / 100.0,
        (player.years_exp or 0) / 20.0,
        1.0 / (adp + 1.0),
        0.0,          # projected_points: not yet integrated
        1.0 / 1000.0, # position_rank: not yet integrated
        1.0 if player.team else 0.0,
        1.0 if player.injury_status else 0.0,
    ]


def _default_player_features() -> List[float]:
    """
    Return a zero-filled 9-dim player feature vector used for padding.

    Returns:
        List[float]: Nine zeros, one per player feature dimension.
    """
    return [0.0] * 9


def _build_context(
    pick: Any,
    roster_before: Dict[str, int],
    total_picks: int,
) -> List[float]:
    """
    Encode draft context into the 8-dim vector used by TeamOwnerDraftModel.

    Args:
        pick: DraftPick ORM row containing pick_no, draft_slot, and round.
        roster_before: Position counts for the owner's roster before this pick.
        total_picks: Total picks in the draft for normalization.

    Returns:
        List[float]: 8-dim vector — roster_needs, draft_pos, picks_remaining, round,
            qb_need, rb_slots_norm, wr_slots_norm, flex_need.
    """
    picks_remaining = max(0, total_picks - pick.pick_no)
    qb_count = roster_before.get("QB", 0)
    rb_count = roster_before.get("RB", 0)
    wr_count = roster_before.get("WR", 0)

    qb_need = 1.0 if qb_count == 0 else 0.0
    rb_slots_norm = max(0.0, (_RB_SLOTS - rb_count)) / _RB_SLOTS
    wr_slots_norm = max(0.0, (_WR_SLOTS - wr_count)) / _WR_SLOTS

    # Simple roster_needs_score: fraction of starting slots still unfilled
    filled = qb_count + rb_count + wr_count + roster_before.get("TE", 0)
    total_starting = int(_QB_SLOTS + _RB_SLOTS + _WR_SLOTS + _TE_SLOTS)
    roster_needs_score = max(0.0, 1.0 - filled / total_starting)

    return [
        roster_needs_score,
        (pick.draft_slot or pick.pick_no) / _PICK_NORM,
        picks_remaining / _PICK_NORM,
        (pick.round or 1) / _ROUND_NORM,
        qb_need,
        rb_slots_norm,
        wr_slots_norm,
        0.5,  # flex_need: neutral default
    ]


def _compute_owner_profile(
    owner_picks: List[Any],
    players_map: Dict[str, Any],
    adp_data: Dict[str, Any],
) -> List[float]:
    """
    Derive the 26-dim owner profile vector from historical draft picks.

    Args:
        owner_picks: DraftPick rows for the target owner.
        players_map: Dict mapping player_id to Player ORM rows.
        adp_data: ADP metrics dict from calculate_adp_from_picks.

    Returns:
        List[float]: 26 floats — position pick rates by tier (18) plus behavioural tendencies (8).
    """
    tier_counts: Dict[str, Dict[str, int]] = {
        "early": defaultdict(int),  # rounds 1-4
        "mid": defaultdict(int),    # rounds 5-8
        "late": defaultdict(int),   # rounds 9+
    }
    tier_totals: Dict[str, int] = {"early": 0, "mid": 0, "late": 0}

    adp_deviations: List[float] = []
    sleeper_picks = 0
    qb_early = 0
    te_premium = 0
    total = len(owner_picks)

    for pick in owner_picks:
        if not pick.player_id:
            continue
        player = players_map.get(pick.player_id)
        pos = (player.position if player and player.position else None) or "UNK"
        if pos not in _POSITION_MAP:
            pos = "UNK"

        round_no = pick.round or 99
        if round_no <= 4:
            tier = "early"
        elif round_no <= 8:
            tier = "mid"
        else:
            tier = "late"

        if pos != "UNK":
            tier_counts[tier][pos] += 1
        tier_totals[tier] += 1

        # ADP deviation: how early (reach) or late (value) relative to consensus
        consensus_adp = adp_data.get(pick.player_id, {}).get("adp", pick.pick_no)
        if consensus_adp and float(consensus_adp) > 0:
            deviation = (pick.pick_no - float(consensus_adp)) / max(float(consensus_adp), 1.0)
            # Map to [0,1]: 0.5=neutral, <0.5=reaches, >0.5=waits
            adp_deviations.append(max(0.0, min(1.0, 0.5 + deviation / 2.0)))
        if float(consensus_adp or 0) > 0 and pick.pick_no < float(consensus_adp):
            sleeper_picks += 1  # drafted earlier than consensus = "sleeper"

        if pos == "QB" and round_no <= 8:
            qb_early += 1
        if pos == "TE" and round_no <= 4:
            te_premium += 1

    def rate(tier: str, pos: str) -> float:
        t = tier_totals.get(tier, 0)
        return tier_counts[tier].get(pos, 0) / t if t > 0 else 0.0

    mean_adp_dev = sum(adp_deviations) / max(len(adp_deviations), 1)
    early_total = tier_totals["early"]

    return [
        # Rounds 1-4 position rates (indices 0-5)
        rate("early", "QB"), rate("early", "RB"), rate("early", "WR"),
        rate("early", "TE"), rate("early", "K"),  rate("early", "DEF"),
        # Rounds 5-8 position rates (indices 6-11)
        rate("mid", "QB"), rate("mid", "RB"), rate("mid", "WR"),
        rate("mid", "TE"), rate("mid", "K"),  rate("mid", "DEF"),
        # Rounds 9+ position rates (indices 12-17)
        rate("late", "QB"), rate("late", "RB"), rate("late", "WR"),
        rate("late", "TE"), rate("late", "K"),  rate("late", "DEF"),
        # Behavioural tendencies (indices 18-25)
        mean_adp_dev,                                      # 18 adp_deviation
        sleeper_picks / max(total, 1),                     # 19 sleeper_pick_rate
        0.0,                                               # 20 handcuff_rate (TODO)
        qb_early / max(total, 1),                          # 21 qb_early_tendency
        te_premium / max(total, 1),                        # 22 te_premium_tendency
        tier_counts["early"]["RB"] / max(early_total, 1),  # 23 rb_heavy_early
        tier_counts["early"]["WR"] / max(early_total, 1),  # 24 wr_heavy_early
        0.5,                                               # 25 pick_consistency (TODO)
    ]
