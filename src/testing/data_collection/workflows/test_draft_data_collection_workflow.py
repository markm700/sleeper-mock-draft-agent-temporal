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
                "draft_pick_trades": [
                    {"league_id": "league-123", "pick_id": "pick-1"},
                    {"league_id": "league-123", "pick_id": "pick-2"},
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

    # Top-level keys
    assert "activity_data" in result
    assert result["draft_data"] == {
        "league_drafts": [
            {"league_id": "league-123", "draft_id": "draft-1"},
            {"league_id": "league-123", "draft_id": "draft-2"},
        ]
    }
    assert result["draft_pick_trades"] == {
        "draft_pick_trades": [
            {"league_id": "league-123", "pick_id": "pick-1"},
            {"league_id": "league-123", "pick_id": "pick-2"},
        ]
    }

    # activity_data should record both activities in order
    assert len(result["activity_data"]) == 2
    first_entry = result["activity_data"][0]
    second_entry = result["activity_data"][1]

    assert first_entry["activity"] == "get_league_drafts"
    assert first_entry["result"] == result["draft_data"]

    assert second_entry["activity"] == "get_specific_draft_picks"
    assert second_entry["result"] == result["draft_pick_trades"]

    # Verify execute_activity was called twice with expected parameters
    assert len(activity_calls) == 2

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
    assert getattr(picks_params, "league_id", None) == "league-123"
    assert "start_to_close_timeout" in kwargs2
    assert "retry_policy" in kwargs2
