import pytest

from workflows.player_data_collection import PlayerDataCollectionWorkflow


@pytest.mark.asyncio
async def test_player_data_collection_runs_activity_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PlayerDataCollectionWorkflow executes get_all_player_data activity."""
    activity_calls: list[tuple[object, tuple[object, ...], dict]] = []

    # Mock workflow.info() to provide run_id
    class MockWorkflowInfo:
        run_id = "test-run-id-1234"

    def _fake_workflow_info() -> MockWorkflowInfo:
        return MockWorkflowInfo()

    async def _fake_execute_activity(fn: object, *args: object, **kwargs: object) -> dict:
        activity_calls.append((fn, args, kwargs))
        name = getattr(fn, "__name__", None)
        if name == "get_all_player_data":
            return {
                "total_found_players": 8500,
                "upserted_players": 8500,
            }
        raise AssertionError(f"Unexpected activity function passed to execute_activity: {name}")

    monkeypatch.setattr(
        "workflows.player_data_collection.workflow.info",
        _fake_workflow_info,
    )
    monkeypatch.setattr(
        "workflows.player_data_collection.workflow.execute_activity",
        _fake_execute_activity,
    )

    wf = PlayerDataCollectionWorkflow()

    result = await wf.run()

    # Top-level key
    assert "activity_data" in result

    # activity_data should record the player data activity
    assert len(result["activity_data"]) == 1
    
    first_entry = result["activity_data"][0]
    assert first_entry["activity"] == "get_all_player_data"
    assert "player_database_operations" in first_entry
    assert first_entry["player_database_operations"]["total_found_players"] == 8500
    assert first_entry["player_database_operations"]["upserted_players"] == 8500

    # Verify execute_activity was called once with expected parameters
    assert len(activity_calls) == 1

    fn1, args1, kwargs1 = activity_calls[0]
    assert getattr(fn1, "__name__", None) == "get_all_player_data"
    assert len(args1) == 0  # No input parameters for this activity
    assert "start_to_close_timeout" in kwargs1
    assert "retry_policy" in kwargs1
    assert "activity_id" in kwargs1


@pytest.mark.asyncio
async def test_player_data_collection_handles_partial_upsert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test workflow handles case where not all players are upserted successfully."""
    activity_calls: list[tuple[object, tuple[object, ...], dict]] = []

    # Mock workflow.info() to provide run_id
    class MockWorkflowInfo:
        run_id = "test-run-id-5678"

    def _fake_workflow_info() -> MockWorkflowInfo:
        return MockWorkflowInfo()

    async def _fake_execute_activity(fn: object, *args: object, **kwargs: object) -> dict:
        activity_calls.append((fn, args, kwargs))
        name = getattr(fn, "__name__", None)
        if name == "get_all_player_data":
            # Simulate scenario where some players failed to upsert
            return {
                "total_found_players": 8500,
                "upserted_players": 8475,  # 25 players failed
            }
        raise AssertionError(f"Unexpected activity function: {name}")

    monkeypatch.setattr(
        "workflows.player_data_collection.workflow.info",
        _fake_workflow_info,
    )
    monkeypatch.setattr(
        "workflows.player_data_collection.workflow.execute_activity",
        _fake_execute_activity,
    )

    wf = PlayerDataCollectionWorkflow()

    result = await wf.run()

    # Verify workflow completes successfully even with partial upsert
    assert "activity_data" in result
    assert len(result["activity_data"]) == 1
    
    player_ops = result["activity_data"][0]["player_database_operations"]
    assert player_ops["total_found_players"] == 8500
    assert player_ops["upserted_players"] == 8475


@pytest.mark.asyncio
async def test_player_data_collection_handles_no_players(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test workflow handles empty player data response."""
    activity_calls: list[tuple[object, tuple[object, ...], dict]] = []

    # Mock workflow.info() to provide run_id
    class MockWorkflowInfo:
        run_id = "test-run-id-abcd"

    def _fake_workflow_info() -> MockWorkflowInfo:
        return MockWorkflowInfo()

    async def _fake_execute_activity(fn: object, *args: object, **kwargs: object) -> dict:
        activity_calls.append((fn, args, kwargs))
        name = getattr(fn, "__name__", None)
        if name == "get_all_player_data":
            # Simulate empty response
            return {
                "total_found_players": 0,
                "upserted_players": 0,
            }
        raise AssertionError(f"Unexpected activity function: {name}")

    monkeypatch.setattr(
        "workflows.player_data_collection.workflow.info",
        _fake_workflow_info,
    )
    monkeypatch.setattr(
        "workflows.player_data_collection.workflow.execute_activity",
        _fake_execute_activity,
    )

    wf = PlayerDataCollectionWorkflow()

    result = await wf.run()

    # Verify workflow completes successfully with no players
    assert "activity_data" in result
    assert len(result["activity_data"]) == 1
    
    player_ops = result["activity_data"][0]["player_database_operations"]
    assert player_ops["total_found_players"] == 0
    assert player_ops["upserted_players"] == 0
