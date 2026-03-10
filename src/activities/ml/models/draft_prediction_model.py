"""
PyTorch draft prediction model with multi-input architecture.
"""

import torch
import torch.nn as nn
from typing import List


class DraftPredictionModel(nn.Module):
    """
    Multi-input PyTorch model for fantasy football draft prediction.
    
    Takes three separate inputs:
    - Player features (stats, ADP, position, etc.)
    - Owner preferences (positional bias, draft tendencies)
    - Draft context (roster needs, available players)
    
    Outputs probability distribution over all available players.
    
    Example:
        >>> model = DraftPredictionModel(
        ...     player_feature_dim=50,
        ...     owner_feature_dim=20,
        ...     draft_context_dim=15,
        ...     num_players=500
        ... )
        >>> player_x = torch.randn(32, 50)  # batch of 32
        >>> owner_x = torch.randn(32, 20)
        >>> draft_x = torch.randn(32, 15)
        >>> predictions = model(player_x, owner_x, draft_x)
        >>> predictions.shape  # (32, 500)
    """
    
    def __init__(
        self,
        player_feature_dim: int,
        owner_feature_dim: int,
        draft_context_dim: int,
        num_players: int,
        hidden_layers: List[int] = [256, 128, 64],
        dropout_rate: float = 0.3
    ):
        """
        Initialize draft prediction model.
        
        Args:
            player_feature_dim: Number of player features
            owner_feature_dim: Number of owner preference features
            draft_context_dim: Number of draft context features
            num_players: Number of possible players (output size)
            hidden_layers: List of hidden layer sizes
            dropout_rate: Dropout probability for regularization
        """
        super().__init__()
        
        self.player_feature_dim = player_feature_dim
        self.owner_feature_dim = owner_feature_dim
        self.draft_context_dim = draft_context_dim
        self.num_players = num_players
        
        # Input encoders with batch normalization
        self.player_encoder = nn.Sequential(
            nn.Linear(player_feature_dim, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128)
        )
        
        self.owner_encoder = nn.Sequential(
            nn.Linear(owner_feature_dim, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64)
        )
        
        self.draft_encoder = nn.Sequential(
            nn.Linear(draft_context_dim, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32)
        )
        
        # Combined feature dimension
        combined_dim = 128 + 64 + 32  # 224
        
        # Build hidden layers dynamically
        layers = []
        input_dim = combined_dim
        
        for hidden_dim in hidden_layers:
            layers.extend([
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout_rate)
            ])
            input_dim = hidden_dim
        
        # Output layer (no activation, we'll apply softmax in forward)
        layers.append(nn.Linear(input_dim, num_players))
        
        self.prediction_layers = nn.Sequential(*layers)
    
    def forward(
        self,
        player_features: torch.Tensor,
        owner_features: torch.Tensor,
        draft_context: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass through the model.
        
        Args:
            player_features: Tensor of shape (batch_size, player_feature_dim)
            owner_features: Tensor of shape (batch_size, owner_feature_dim)
            draft_context: Tensor of shape (batch_size, draft_context_dim)
        
        Returns:
            Probability distribution over players, shape (batch_size, num_players)
        """
        # Encode each input stream
        player_enc = self.player_encoder(player_features)
        owner_enc = self.owner_encoder(owner_features)
        draft_enc = self.draft_encoder(draft_context)
        
        # Concatenate all features
        combined = torch.cat([player_enc, owner_enc, draft_enc], dim=1)
        
        # Pass through prediction layers
        logits = self.prediction_layers(combined)
        
        # Apply softmax for probability distribution
        probabilities = torch.softmax(logits, dim=1)
        
        return probabilities
    
    def get_config(self) -> dict:
        """Get model configuration for saving/loading."""
        return {
            "player_feature_dim": self.player_feature_dim,
            "owner_feature_dim": self.owner_feature_dim,
            "draft_context_dim": self.draft_context_dim,
            "num_players": self.num_players,
        }
