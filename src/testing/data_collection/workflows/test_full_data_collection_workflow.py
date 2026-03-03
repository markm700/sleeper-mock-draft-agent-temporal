import pytest

from ....workflows.full_data_collection import (
    FullDataCollectionWorkflow,
    FullDataCollectionWorkflowParams,
)
from ....workflows.team_owner_data_collection import TeamOwnerDataCollectionWorkflow
from ....workflows.league_data_collection import LeagueDataCollectionWorkflow, LeagueDataCollectionWorkflowParams


@pytest.mark.asyncio
async def test_full_data_collection_chains_owner_and_league_workflows_with_latest_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child_calls: list[tuple[object, tuple[object, ...], dict]] = []

    # Mock workflow.info() to provide run_id
    class MockWorkflowInfo:
        run_id = "test-run-id-full-1234"

    def _fake_workflow_info() -> MockWorkflowInfo:
        return MockWorkflowInfo()

    async def _fake_execute_child_workflow(
        wf: object, *args: object, **kwargs: object
    ) -> dict:
        child_calls.append((wf, args, kwargs))
        # Check by function qualified name instead of identity comparison
        wf_name = getattr(wf, "__qualname__", "")
        
        # First call: team-owner-data-collection
        if wf_name == "TeamOwnerDataCollectionWorkflow.run":
            # Minimal shape compatible with TeamOwnerDataCollectionWorkflow output,
            # including multiple seasons to test latest-season selection.
            return {
                "activity_data": [
                    {
                        "activity": "get_team_owner_data",
                        "result": {
                            "user_leagues": {
                                "2022": [
                                    {"league_id": "league-older", "name": "My League"},
                                ],
                                "2024": [
                                    {"league_id": "league-latest", "name": "My League"},
                                ],
                            }
                        },
                    }
                ]
            }
        # Second call: league-data-collection
        if wf_name == "LeagueDataCollectionWorkflow.run":
            return {"activity_data": ["league-activity"], "other": "league-result"}
        # Third call: player-data-collection
        if wf_name == "PlayerDataCollectionWorkflow.run":
            return {
                "activity_data": [
                    {
                        "activity": "get_all_player_data",
                        "player_database_operations": {
                            "total_found_players": 8500,
                            "upserted_players": 8500,
                        }
                    }
                ]
            }
        raise AssertionError(f"Unexpected child workflow: {wf} (qualified name: {wf_name})")

    monkeypatch.setattr(
        "workflows.full_data_collection.workflow.info",
        _fake_workflow_info,
    )
    monkeypatch.setattr(
        "workflows.full_data_collection.workflow.execute_child_workflow",
        _fake_execute_child_workflow,
    )

    wf = FullDataCollectionWorkflow()
    params = FullDataCollectionWorkflowParams(
        username="some_user",
        league_name="My League",
    )

    result = await wf.run(params)

    # Validate top-level result
    assert result["username"] == "some_user"
    assert result["league_name"] == "My League"
    # Should pick the latest season's league_id
    assert result["league_id"] == "league-latest"

    workflow_data = result["workflow_data"]
    assert len(workflow_data) == 3  # team_owner + league + player workflows

    first_step = workflow_data[0]
    assert first_step["workflow"] == "team-owner-data-collection"
    assert "activity_data" in first_step["result"]

    second_step = workflow_data[1]
    assert second_step["workflow"] == "league-data-collection"
    assert second_step["league_id"] == "league-latest"
    assert second_step["result"] == {"activity_data": ["league-activity"], "other": "league-result"}

    third_step = workflow_data[2]
    assert third_step["workflow"] == "player-data-collection"
    assert "activity_data" in third_step["result"]
    assert third_step["result"]["activity_data"][0]["activity"] == "get_all_player_data"

    # Validate child workflow invocations
    assert len(child_calls) == 3  # team_owner + league + player

    wf1, args1, kwargs1 = child_calls[0]
    assert wf1.__qualname__ == "TeamOwnerDataCollectionWorkflow.run"
    assert len(args1) == 1
    owner_params = args1[0]
    assert getattr(owner_params, "username", None) == "some_user"
    assert getattr(owner_params, "league_name", None) == "My League"
    assert "retry_policy" in kwargs1

    wf2, args2, kwargs2 = child_calls[1]
    assert wf2.__qualname__ == "LeagueDataCollectionWorkflow.run"
    assert len(args2) == 1
    league_params = args2[0]
    # Check attributes instead of isinstance to avoid import path issues
    assert hasattr(league_params, "league_id")
    assert getattr(league_params, "league_id", None) == "league-latest"
    assert "retry_policy" in kwargs2

    wf3, args3, kwargs3 = child_calls[2]
    assert wf3.__qualname__ == "PlayerDataCollectionWorkflow.run"
    assert len(args3) == 0  # No input parameters for player workflow
    assert "retry_policy" in kwargs3
