import pytest

from ....workflows.draft_data_collection import (
    DraftDataCollectionWorkflow,
    DraftDataCollectionWorkflowParams,
)


@pytest.mark.asyncio
async def test_draft_data_collection_runs_activities_and_returns_aggregated_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activity_calls: list[tuple[object, tuple[object, ...], dict]] = []

    async def _fake_execute_activity(fn: object, *args: object, **kwargs: object) -> dict:
        activity_calls.append((fn, args, kwargs))
        name = getattr(fn, "__name__", None)
        if name == "get_league_drafts":
            return {
                "league_drafts": [
                    {"league_id": "league-123", "draft_id": "draft-1"},
                    {"league_id": "league-123", "draft_id": "draft-2"},
                ]
            }
        if name == "get_specific_draft_picks":
            return {
                "draft_picks": [
                    {"draft_id": "draft-1", "pick_no": 1, "player_id": "player-1"},
                    {"draft_id": "draft-1", "pick_no": 2, "player_id": "player-2"},
                ]
            }
        if name == "get_traded_draft_picks":
            return {
                "traded_draft_picks": [
                    {"season": "2025", "round": 1, "roster_id": 2},
                    {"season": "2025", "round": 3, "roster_id": 1},
                ]
            }
        raise AssertionError(f"Unexpected activity function passed to execute_activity: {name}")

    monkeypatch.setattr(
        "src.workflows.draft_data_collection.workflow.execute_activity",
        _fake_execute_activity,
    )

    wf = DraftDataCollectionWorkflow()
    params = DraftDataCollectionWorkflowParams(league_id="league-123")

    result = await wf.run(params)

    # Top-level key
    assert "activity_data" in result

    # activity_data should record all three activities in order
    assert len(result["activity_data"]) == 3
    
    first_entry = result["activity_data"][0]
    assert first_entry["activity"] == "get_league_drafts"
    assert "draft_data" in first_entry
    assert len(first_entry["draft_data"]["league_drafts"]) == 2

    second_entry = result["activity_data"][1]
    assert second_entry["activity"] == "get_specific_draft_picks"
    assert second_entry["total_draft_picks"] == 2
    assert "draft_picks" in second_entry

    third_entry = result["activity_data"][2]
    assert third_entry["activity"] == "get_traded_draft_picks"
    assert third_entry["total_traded_picks"] == 2
    assert "draft_pick_trades" in third_entry

    # Verify execute_activity was called three times with expected parameters
    assert len(activity_calls) == 3

    fn1, args1, kwargs1 = activity_calls[0]
    assert getattr(fn1, "__name__", None) == "get_league_drafts"
    assert len(args1) == 1
    drafts_params = args1[0]
    assert getattr(drafts_params, "league_id", None) == "league-123"
    assert "start_to_close_timeout" in kwargs1
    assert "retry_policy" in kwargs1

    fn2, args2, kwargs2 = activity_calls[1]
    assert getattr(fn2, "__name__", None) == "get_specific_draft_picks"
    assert len(args2) == 1
    picks_params = args2[0]
    assert getattr(picks_params, "draft_id", None) == "draft-1"
    assert "start_to_close_timeout" in kwargs2
    assert "retry_policy" in kwargs2

    fn3, args3, kwargs3 = activity_calls[2]
    assert getattr(fn3, "__name__", None) == "get_traded_draft_picks"
    assert len(args3) == 1
    traded_params = args3[0]
    assert getattr(traded_params, "league_id", None) == "league-123"
    assert getattr(traded_params, "season", None) == "2025"  # Verify default season is passed
    assert "start_to_close_timeout" in kwargs3
    assert "retry_policy" in kwargs3
