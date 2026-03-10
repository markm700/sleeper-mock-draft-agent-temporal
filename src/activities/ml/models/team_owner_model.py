"""
Team-owner-centric PyTorch draft prediction model.

Each model instance is trained to represent a specific fantasy football team owner
and predict which player that owner will draft during mock draft simulations.

Personality traits can optionally modulate the base prediction — sometimes an owner
drafts purely on historical pattern; other times they "act on instinct" based on their
personality (upside-chasing, contrarian tendencies, etc.).
"""

import torch
import torch.nn as nn
from typing import List, Tuple


# Personality trait names and indices — a stable contract for feature vectors.
PERSONALITY_TRAITS: List[str] = [
    "upside_seeking",           # 0: Preference for boom-or-bust players (0=floor, 1=ceiling)
    "floor_preference",         # 1: Preference for safe, consistent players
    "adp_reach_tendency",       # 2: Tendency to reach early or wait (0=waits, 0.5=neutral, 1=reaches)
    "injury_tolerance",         # 3: Willingness to draft risky/injured players (0=avoids, 1=accepts)
    "rookie_bias",              # 4: Bias toward drafting rookies (0=avoids, 0.5=neutral, 1=targets)
    "name_recognition",         # 5: Drafts recognizable names vs. stats (0=pure stats, 1=name-first)
    "contrarian",               # 6: Goes against consensus ADP (0=follows crowd, 1=contrarian)
    "positional_stubbornness",  # 7: Sticks to positional strategy vs. best player available
]
NUM_PERSONALITY_TRAITS: int = len(PERSONALITY_TRAITS)

# Owner profile feature names — derived from historical draft data.
OWNER_PROFILE_FEATURES: List[str] = [
    # Position pick rates by round tier (fraction of picks in that tier spent on each position)
    "early_qb_rate",   # 0:  QB rate rounds 1-4
    "early_rb_rate",   # 1:  RB rate rounds 1-4
    "early_wr_rate",   # 2:  WR rate rounds 1-4
    "early_te_rate",   # 3:  TE rate rounds 1-4
    "early_k_rate",    # 4:  K  rate rounds 1-4
    "early_def_rate",  # 5:  DEF rate rounds 1-4
    "mid_qb_rate",     # 6:  QB rate rounds 5-8
    "mid_rb_rate",     # 7:  RB rate rounds 5-8
    "mid_wr_rate",     # 8:  WR rate rounds 5-8
    "mid_te_rate",     # 9:  TE rate rounds 5-8
    "mid_k_rate",      # 10: K  rate rounds 5-8
    "mid_def_rate",    # 11: DEF rate rounds 5-8
    "late_qb_rate",    # 12: QB rate rounds 9+
    "late_rb_rate",    # 13: RB rate rounds 9+
    "late_wr_rate",    # 14: WR rate rounds 9+
    "late_te_rate",    # 15: TE rate rounds 9+
    "late_k_rate",     # 16: K  rate rounds 9+
    "late_def_rate",   # 17: DEF rate rounds 9+
    # Tendencies derived from historical picks
    "adp_deviation",        # 18: Mean ADP deviation (0=waits, 0.5=neutral, 1=reaches)
    "sleeper_pick_rate",    # 19: Fraction of picks that were below consensus value (0-1)
    "handcuff_rate",        # 20: Fraction of picks that were handcuffs (0-1)
    "qb_early_tendency",    # 21: How often QB drafted before round 8 (0-1)
    "te_premium_tendency",  # 22: How often TE1 drafted before round 5 (0-1)
    "rb_heavy_early",       # 23: Fraction of rounds 1-4 spent on RB
    "wr_heavy_early",       # 24: Fraction of rounds 1-4 spent on WR
    "pick_consistency",     # 25: Consistency vs. consensus rank order (0=chaotic, 1=consistent)
]
OWNER_PROFILE_DIM: int = len(OWNER_PROFILE_FEATURES)

# Default player and context dimensions (must match _prepare_player_features_only /
# _prepare_draft_context_features in predict_player_pick.py).
PLAYER_FEATURE_DIM: int = 9
DRAFT_CONTEXT_DIM: int = 8
NUM_POSITIONS: int = 6  # QB, RB, WR, TE, K, DEF


class TeamOwnerDraftModel(nn.Module):
    """
    Owner-centric draft prediction model for fantasy football mock draft simulation.

    Models a specific team owner as an individual decision-maker combining:
    - Historical pick patterns (owner_profile): what this owner has drafted in the past
    - Personality traits: behavioral tendencies that can stochastically modulate picks

    The personality gate allows trait-driven behavior to optionally override the
    base data-driven prediction. This mirrors how real owners sometimes draft on
    instinct or personal bias rather than pure logic — and how that behavior varies
    pick to pick.

    Architecture
    ------------
    Learning-to-rank design: each candidate player is scored independently, so the
    batch dimension equals the number of available players being evaluated.

    Four independent input encoders feed into two paths:

        Base path  (always active):
            [player_enc + profile_enc + context_enc] → base_fusion → base_shared (128)

        Personality path  (scaled by personality_influence_scale):
            [personality_enc + base_shared] → personality_gate → modulation delta (128)

        Final shared = base_shared + personality_influence_scale × modulation
        → three output heads: pick_score, confidence, position_priority

    Using personality_influence_scale=0.0 produces purely history-driven predictions;
    1.0 fully engages personality. By randomizing this value per pick during simulation
    (see predict_with_random_personality), each pick varies naturally.

    Inputs
    ------
    player_features         : (n_candidates, player_feature_dim)  per-player stats / fantasy metrics
    owner_profile           : (n_candidates, owner_profile_dim)   tiled owner historical tendencies
    draft_context           : (n_candidates, draft_context_dim)   tiled current roster state
    personality_traits      : (n_candidates, personality_dim)     tiled personality trait vector
    personality_influence_scale : float  0=history-only  1=full personality

    Outputs
    -------
    pick_score        : (n_candidates, 1)          raw affinity score per candidate player;
                        apply softmax across all candidates to get pick probabilities
    confidence        : (n_candidates, 1)          sigmoid score in [0, 1] per candidate
    position_priority : (n_candidates, num_positions) positional preference vector

    Inference pattern
    -----------------
    >>> n = len(available_players)
    >>> player_x  = torch.tensor(player_feats, ...)          # (n, player_dim)
    >>> profile_x = owner_profile_tensor.expand(n, -1)       # (n, profile_dim)
    >>> ctx_x     = draft_ctx_tensor.expand(n, -1)           # (n, ctx_dim)
    >>> traits_x  = personality_tensor.expand(n, -1)         # (n, personality_dim)
    >>>
    >>> # Deterministic — no personality
    >>> scores, conf, pos_prio = model(player_x, profile_x, ctx_x, traits_x, 0.0)
    >>> pick_probs = torch.softmax(scores.squeeze(1), dim=0)  # probability per candidate
    >>>
    >>> # Stochastic — randomized personality influence per pick
    >>> scores, conf, pos_prio, influence = model.predict_with_random_personality(
    ...     player_x, profile_x, ctx_x, traits_x
    ... )
    >>> pick_probs = torch.softmax(scores.squeeze(1), dim=0)
    """

    def __init__(
        self,
        player_feature_dim: int,
        owner_profile_dim: int,
        draft_context_dim: int,
        personality_dim: int = NUM_PERSONALITY_TRAITS,
        num_positions: int = NUM_POSITIONS,
        hidden_dim: int = 256,
        dropout_rate: float = 0.3,
    ):
        """
        Initialize team owner draft model.

        Args:
            player_feature_dim: Number of per-player features (e.g. 9)
            owner_profile_dim:  Number of historical profile features (e.g. 26)
            draft_context_dim:  Number of draft-state features (e.g. 8)
            personality_dim:    Number of personality traits (default 8)
            num_positions:      Number of fantasy positions (default 6: QB/RB/WR/TE/K/DEF)
            hidden_dim:         Width of the shared fusion layers
            dropout_rate:       Dropout probability for regularization
        """
        super().__init__()

        self.player_feature_dim = player_feature_dim
        self.owner_profile_dim = owner_profile_dim
        self.draft_context_dim = draft_context_dim
        self.personality_dim = personality_dim
        self.num_positions = num_positions
        self.hidden_dim = hidden_dim

        # ── Input Encoders ────────────────────────────────────────────────────

        # Player features: per-player stats, ADP, position, etc.
        self.player_encoder = nn.Sequential(
            nn.Linear(player_feature_dim, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
        )

        # Owner historical profile: positional bias, pick tendencies, etc.
        self.profile_encoder = nn.Sequential(
            nn.Linear(owner_profile_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )

        # Draft context: roster state, round number, positional needs.
        self.context_encoder = nn.Sequential(
            nn.Linear(draft_context_dim, 32),
            nn.LayerNorm(32),
            nn.ReLU(),
        )

        # Personality traits: behavioral characteristics.
        self.personality_encoder = nn.Sequential(
            nn.Linear(personality_dim, 32),
            nn.LayerNorm(32),
            nn.ReLU(),
        )

        # ── Base Fusion (history + stats driven) ─────────────────────────────

        base_input_dim = 128 + 64 + 32  # player + profile + context = 224
        self.base_fusion = nn.Sequential(
            nn.Linear(base_input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
        )

        # ── Personality Modulation Gate ───────────────────────────────────────
        # Takes [personality_enc | base_shared] and produces an additive delta.
        # Tanh output keeps the modulation bounded in [-1, 1] per dimension.
        personality_gate_input_dim = 32 + 128  # personality_rep + base_shared
        self.personality_gate = nn.Sequential(
            nn.Linear(personality_gate_input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.Tanh(),
        )

        # ── Output Heads ──────────────────────────────────────────────────────

        # Head 1: pick affinity score — one scalar per candidate player.
        # Caller applies softmax across all candidates to get pick probabilities.
        self.pick_score_head = nn.Linear(128, 1)

        # Head 2: confidence score
        self.confidence_head = nn.Sequential(
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

        # Head 3: positional priority
        self.position_head = nn.Sequential(
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, num_positions),
        )

    def forward(
        self,
        player_features: torch.Tensor,
        owner_profile: torch.Tensor,
        draft_context: torch.Tensor,
        personality_traits: torch.Tensor,
        personality_influence_scale: float = 0.5,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            player_features:            (n_candidates, player_feature_dim)
            owner_profile:              (n_candidates, owner_profile_dim) — tiled per candidate
            draft_context:              (n_candidates, draft_context_dim) — tiled per candidate
            personality_traits:         (n_candidates, personality_dim) — tiled per candidate
            personality_influence_scale: Scalar 0–1.
                0.0 = purely historical / data-driven (no personality effect).
                1.0 = full personality influence.
                Randomize per pick for simulation variety.

        Returns:
            Tuple[pick_score, confidence, position_priority]
            - pick_score:       (n_candidates, 1) — raw affinity per candidate;
                                apply softmax across dim=0 to get pick probabilities
            - confidence:       (n_candidates, 1) — sigmoid score in [0, 1]
            - position_priority:(n_candidates, num_positions) — softmax over positions
        """
        # Encode the four input streams
        player_enc = self.player_encoder(player_features)         # (batch, 128)
        profile_enc = self.profile_encoder(owner_profile)         # (batch,  64)
        context_enc = self.context_encoder(draft_context)         # (batch,  32)
        personality_enc = self.personality_encoder(personality_traits)  # (batch, 32)

        # Base path: fuse player, profile, and context
        base_combined = torch.cat([player_enc, profile_enc, context_enc], dim=1)
        base_shared = self.base_fusion(base_combined)             # (batch, 128)

        # Personality path: learn how traits modulate the base representation
        personality_input = torch.cat([personality_enc, base_shared], dim=1)
        personality_modulation = self.personality_gate(personality_input)   # (batch, 128)

        # Mix: personality_influence_scale blends base (history) with personality
        final_shared = base_shared + personality_influence_scale * personality_modulation

        # Output heads
        pick_score = self.pick_score_head(final_shared)      # (n_candidates, 1)

        confidence_logits = self.confidence_head(final_shared)
        confidence = torch.sigmoid(confidence_logits)        # (n_candidates, 1)

        position_logits = self.position_head(final_shared)
        position_priority = torch.softmax(position_logits, dim=1)  # (n_candidates, num_positions)

        return pick_score, confidence, position_priority

    def predict_with_random_personality(
        self,
        player_features: torch.Tensor,
        owner_profile: torch.Tensor,
        draft_context: torch.Tensor,
        personality_traits: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
        """
        Predict with a randomly sampled personality influence scale.

        Simulates the pick-to-pick unpredictability of human drafters: some picks
        are purely data-driven, others are strongly personality-driven. The influence
        value used is returned so callers can log or display it.

        Returns:
            (pick_score, confidence, position_priority, influence_used)
            - pick_score:    (n_candidates, 1) — raw affinity scores; softmax to get probs
            - influence_used: float in [0, 1] — the randomly sampled scale that was applied
        """
        influence = torch.rand(1).item()
        pick_score, confidence, position_priority = self.forward(
            player_features,
            owner_profile,
            draft_context,
            personality_traits,
            personality_influence_scale=influence,
        )
        return pick_score, confidence, position_priority, influence

    def get_config(self) -> dict:
        """Return model configuration for serialization / re-instantiation."""
        return {
            "model_type": "TeamOwnerDraftModel",
            "player_feature_dim": self.player_feature_dim,
            "owner_profile_dim": self.owner_profile_dim,
            "draft_context_dim": self.draft_context_dim,
            "personality_dim": self.personality_dim,
            "num_positions": self.num_positions,
            "hidden_dim": self.hidden_dim,
        }
