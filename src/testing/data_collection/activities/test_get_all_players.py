import pytest

from activities.players.get_all_players import get_all_player_data
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_all_player_data_fetches_and_batch_upserts_players(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_all_player_data fetches player data and batch upserts to database."""
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.players.get_all_players.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.players.get_all_players.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    result = await get_all_player_data()

    # Verify result structure
    assert "total_found_players" in result
    assert "upserted_players" in result
    
    # Dummy client returns 3 players
    assert result["total_found_players"] == 3
    assert result["upserted_players"] == 3

    # Verify batch upsert was called for Player model
    assert dummy_postgres.count_batch_upserts_for_model("Player") == 1
    
    # Verify all players were batch upserted
    players = dummy_postgres.get_batch_upserted_by_model("Player")
    assert len(players) == 3
    
    # Verify player data structure for first player
    player_1 = next((p for p in players if p["player_id"] == "player_1"), None)
    assert player_1 is not None
    assert player_1["full_name"] == "Patrick Mahomes"
    assert player_1["position"] == "QB"
    assert player_1["team"] == "KC"
    assert player_1["age"] == 28
    assert player_1["years_exp"] == 6
    
    # Verify external IDs are mapped
    assert player_1["espn_id"] == "3139477"
    assert player_1["yahoo_id"] == "30123"
    
    # Verify injury data is None for healthy player
    assert player_1["injury_status"] is None
    
    # Verify player with injury data
    player_2 = next((p for p in players if p["player_id"] == "player_2"), None)
    assert player_2 is not None
    assert player_2["full_name"] == "Christian McCaffrey"
    assert player_2["injury_status"] == "Questionable"
    assert player_2["injury_body_part"] == "Ankle"
    assert player_2["injury_notes"] == "Limited in practice"
    
    # Verify third player
    player_3 = next((p for p in players if p["player_id"] == "player_3"), None)
    assert player_3 is not None
    assert player_3["full_name"] == "Justin Jefferson"
    assert player_3["position"] == "WR"
    assert player_3["team"] == "MIN"


@pytest.mark.asyncio
async def test_get_all_player_data_handles_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_all_player_data handles empty player data gracefully."""
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    # Override get_nfl_players to return empty dict
    async def _fake_get_nfl_players() -> dict:
        return {}
    
    dummy_sleeper.get_nfl_players = _fake_get_nfl_players

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.players.get_all_players.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.players.get_all_players.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    result = await get_all_player_data()

    # Verify result structure
    assert result["total_found_players"] == 0
    assert result["upserted_players"] == 0
    
    # Verify no batch upsert was attempted
    assert dummy_postgres.count_batch_upserts_for_model("Player") == 0


@pytest.mark.asyncio
async def test_get_all_player_data_skips_invalid_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_all_player_data skips invalid player entries."""
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    # Override get_nfl_players to return mixed valid/invalid data
    async def _fake_get_nfl_players() -> dict:
        return {
            "player_1": {
                "player_id": "player_1",
                "full_name": "Valid Player",
                "position": "QB",
            },
            "": {  # Invalid: empty player_id key
                "full_name": "Invalid Player 1",
            },
            "player_2": "not_a_dict",  # Invalid: not a dict
            "player_3": {
                "player_id": "player_3",
                "full_name": "Another Valid Player",
                "position": "RB",
            },
        }
    
    dummy_sleeper.get_nfl_players = _fake_get_nfl_players

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.players.get_all_players.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.players.get_all_players.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    result = await get_all_player_data()

    # Verify only valid players were processed
    assert result["total_found_players"] == 4  # Total entries in response
    assert result["upserted_players"] == 2  # Only 2 valid entries
    
    # Verify batch upsert was called once with valid players
    assert dummy_postgres.count_batch_upserts_for_model("Player") == 1
    players = dummy_postgres.get_batch_upserted_by_model("Player")
    assert len(players) == 2
    assert any(p["player_id"] == "player_1" for p in players)
    assert any(p["player_id"] == "player_3" for p in players)
