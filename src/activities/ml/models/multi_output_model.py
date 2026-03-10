"""
PyTorch multi-output draft prediction model.
"""

import torch
import torch.nn as nn


class MultiOutputDraftModel(nn.Module):
    """
    Multi-input, multi-output PyTorch model for draft prediction.
    
    Inputs (3):
    - Player features
    - Owner preferences  
    - Draft context
    
    Outputs (3):
    1. Pick probability - Which player will be picked (softmax over players)
    2. Confidence score - How confident the model is (sigmoid, 0-1)
    3. Position preference - Which position is prioritized (softmax over positions)
    
    Example:
        >>> model = MultiOutputDraftModel(
        ...     player_feature_dim=50,
        ...     owner_feature_dim=20,
        ...     draft_context_dim=15,
        ...     num_players=500
        ... )
        >>> player_x = torch.randn(32, 50)
        >>> owner_x = torch.randn(32, 20)
        >>> draft_x = torch.randn(32, 15)
        >>> pick_prob, confidence, pos_pref = model(player_x, owner_x, draft_x)
        >>> pick_prob.shape  # (32, 500)
        >>> confidence.shape  # (32, 1)
        >>> pos_pref.shape  # (32, 6)
    """
    
    def __init__(
        self,
        player_feature_dim: int,
        owner_feature_dim: int,
        draft_context_dim: int,
        num_players: int,
        num_positions: int = 6  # QB, RB, WR, TE, K, DEF
    ):
        """
        Initialize multi-output draft model.
        
        Args:
            player_feature_dim: Number of player features
            owner_feature_dim: Number of owner preference features
            draft_context_dim: Number of draft context features
            num_players: Number of possible players
            num_positions: Number of positions (default: 6 - QB/RB/WR/TE/K/DEF)
        """
        super().__init__()
        
        self.player_feature_dim = player_feature_dim
        self.owner_feature_dim = owner_feature_dim
        self.draft_context_dim = draft_context_dim
        self.num_players = num_players
        self.num_positions = num_positions
        
        # Input encoders
        self.player_encoder = nn.Sequential(
            nn.Linear(player_feature_dim, 128),
            nn.ReLU()
        )
        
        self.owner_encoder = nn.Sequential(
            nn.Linear(owner_feature_dim, 64),
            nn.ReLU()
        )
        
        self.draft_encoder = nn.Sequential(
            nn.Linear(draft_context_dim, 32),
            nn.ReLU()
        )
        
        # Shared representation layers
        combined_dim = 128 + 64 + 32  # 224
        self.shared_layers = nn.Sequential(
            nn.Linear(combined_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU()
        )
        
        # Output head 1: Pick probability
        self.pick_head = nn.Linear(128, num_players)
        
        # Output head 2: Confidence score
        self.confidence_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
        # Output head 3: Position preference
        self.position_head = nn.Sequential(
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, num_positions)
        )
    
    def forward(
        self,
        player_features: torch.Tensor,
        owner_features: torch.Tensor,
        draft_context: torch.Tensor
    ) -> tuple:
        """
        Forward pass through the model.
        
        Args:
            player_features: (batch_size, player_feature_dim)
            owner_features: (batch_size, owner_feature_dim)
            draft_context: (batch_size, draft_context_dim)
        
        Returns:
            Tuple of (pick_prob, confidence, position_pref)
            - pick_prob: (batch_size, num_players) - probability distribution
            - confidence: (batch_size, 1) - confidence in [0, 1]
            - position_pref: (batch_size, num_positions) - position probabilities
        """
        # Encode inputs
        player_enc = self.player_encoder(player_features)
        owner_enc = self.owner_encoder(owner_features)
        draft_enc = self.draft_encoder(draft_context)
        
        # Combine and process through shared layers
        combined = torch.cat([player_enc, owner_enc, draft_enc], dim=1)
        shared = self.shared_layers(combined)
        
        # Generate three outputs
        
        # 1. Pick probability (softmax over all players)
        pick_logits = self.pick_head(shared)
        pick_prob = torch.softmax(pick_logits, dim=1)
        
        # 2. Confidence score (sigmoid to [0, 1])
        confidence_logits = self.confidence_head(shared)
        confidence = torch.sigmoid(confidence_logits)
        
        # 3. Position preference (softmax over positions)
        position_logits = self.position_head(shared)
        position_pref = torch.softmax(position_logits, dim=1)
        
        return pick_prob, confidence, position_pref
    
    def get_config(self) -> dict:
        """Get model configuration for saving/loading."""
        return {
            "player_feature_dim": self.player_feature_dim,
            "owner_feature_dim": self.owner_feature_dim,
            "draft_context_dim": self.draft_context_dim,
            "num_players": self.num_players,
            "num_positions": self.num_positions,
        }
