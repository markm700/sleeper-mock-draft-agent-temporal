import pytest

from ....workflows.league_data_collection import (
    LeagueDataCollectionWorkflow,
    LeagueDataCollectionWorkflowParams,
)
from ....workflows.draft_data_collection import (
    DraftDataCollectionWorkflow,
    DraftDataCollectionWorkflowParams,
)


@pytest.mark.asyncio
async def test_league_data_collection_invokes_league_activity_and_draft_child_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activity_calls: list[tuple[object, tuple[object, ...], dict]] = []
    child_calls: list[tuple[object, tuple[object, ...], dict]] = []

    async def _fake_execute_activity(fn: object, *args: object, **kwargs: object) -> dict:
        activity_calls.append((fn, args, kwargs))
        # Simulate get_league_data returning a league_id plus extra fields
        if getattr(fn, "__name__", None) == "get_league_data":
            return {
                "league_id": "league-123",
                "league_data": {"name": "my_league", "season": "2024"},
                "league_users": [],
                "league_rosters": [],
            }
        raise AssertionError("Unexpected activity function passed to execute_activity")

    async def _fake_execute_child_workflow(
        wf: object, *args: object, **kwargs: object
    ) -> dict:
        child_calls.append((wf, args, kwargs))
        # Return a simple sentinel payload to verify propagation
        return {"draft_data": "drafts", "draft_pick_trades": "trades"}

    monkeypatch.setattr(
        "src.workflows.league_data_collection.workflow.execute_activity",
        _fake_execute_activity,
    )
    monkeypatch.setattr(
        "src.workflows.league_data_collection.workflow.execute_child_workflow",
        _fake_execute_child_workflow,
    )

    wf = LeagueDataCollectionWorkflow()
    params = LeagueDataCollectionWorkflowParams(league_id="league-123")

    result = await wf.run(params)

    # The workflow should have recorded both the league activity and the draft child workflow
    assert "activity_data" in result
    assert len(result["activity_data"]) == 2

    first_entry = result["activity_data"][0]
    assert first_entry["activity"] == "get_league_data"
    # Activity result structure is opaque to the workflow; we just expect it
    assert "league_data" in first_entry["result"]

    second_entry = result["activity_data"][1]
    assert second_entry["workflow"] == "draft-data-collection"
    assert second_entry["result"] == {
        "draft_data": "drafts",
        "draft_pick_trades": "trades",
    }

    # Verify execute_activity was called once with get_league_data and the correct params
    assert len(activity_calls) == 1
    fn, args, kwargs = activity_calls[0]
    assert getattr(fn, "__name__", None) == "get_league_data"
    assert len(args) == 1
    league_params = args[0]
    assert getattr(league_params, "league_id", None) == "league-123"
    assert "start_to_close_timeout" in kwargs
    assert "retry_policy" in kwargs

    # Verify the child workflow was invoked with the DraftDataCollectionWorkflow and correct params
    assert len(child_calls) == 1
    wf_ref, child_args, child_kwargs = child_calls[0]
    # We call execute_child_workflow with DraftDataCollectionWorkflow.run
    assert wf_ref is DraftDataCollectionWorkflow.run
    assert len(child_args) == 1
    draft_params = child_args[0]
    assert isinstance(draft_params, DraftDataCollectionWorkflowParams)
    assert draft_params.league_id == "league-123"
    assert draft_params.season == "2024"  # Verify season from league_data is passed
    assert child_kwargs == {}
