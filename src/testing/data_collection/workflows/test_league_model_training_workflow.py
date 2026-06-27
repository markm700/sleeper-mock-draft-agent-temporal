import pytest

from workflows.league_model_training import (
    LeagueModelTrainingWorkflow,
    LeagueModelTrainingWorkflowParams,
)


class MockWorkflowInfo:
    run_id = "test-run-id-abcd"


def _fake_workflow_info() -> MockWorkflowInfo:
    return MockWorkflowInfo()


def _adp_result() -> dict:
    return {
        "adp_data": {},
        "num_players": 5,
        "num_picks": 50,
        "num_drafts": 5,
    }


def _child_training_result(user_id: str, skipped: bool = False) -> dict:
    model_name = f"owner_{user_id}_league-1_v1"
    if skipped:
        return {"model_name": model_name, "skipped": True, "reason": "insufficient_training_samples"}
    return {
        "model_name": model_name,
        "model_path": f"/models/{model_name}.joblib",
        "skipped": False,
        "num_boost_round": 100,
        "num_samples": 15,
        "num_query_groups": 15,
    }


@pytest.mark.asyncio
async def test_league_model_training_trains_all_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: discovers 2 owners and trains a child workflow for each."""
    activity_calls: list = []
    child_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "get_league_team_owners":
            return {"owner_user_ids": ["user-1", "user-2"]}
        if name == "calculate_adp_from_picks":
            return _adp_result()
        raise AssertionError(f"Unexpected activity: {name}")

    async def _fake_execute_child_workflow(fn, params, **kwargs) -> dict:
        child_calls.append(params)
        return _child_training_result(params.user_id, skipped=False)

    monkeypatch.setattr("workflows.league_model_training.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.league_model_training.workflow.execute_activity", _fake_execute_activity)
    monkeypatch.setattr("workflows.league_model_training.workflow.execute_child_workflow", _fake_execute_child_workflow)

    wf = LeagueModelTrainingWorkflow()
    params = LeagueModelTrainingWorkflowParams(league_id="league-1", season="2024")
    result = await wf.run(params)

    assert result["num_owners"] == 2
    assert result["num_trained"] == 2
    assert result["num_skipped"] == 0
    assert len(result["owner_results"]) == 2

    # Both activities should have been called once
    activity_names = [name for name, _ in activity_calls]
    assert "get_league_team_owners" in activity_names
    assert "calculate_adp_from_picks" in activity_names

    # Child workflow called once per owner
    assert len(child_calls) == 2
    assert child_calls[0].user_id == "user-1"
    assert child_calls[1].user_id == "user-2"

    # Precomputed ADP is forwarded to each child
    assert child_calls[0].precomputed_adp_data == _adp_result()


@pytest.mark.asyncio
async def test_league_model_training_counts_skipped_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owners whose child workflow returns skipped=True are counted in num_skipped."""
    child_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        if name == "get_league_team_owners":
            return {"owner_user_ids": ["user-1", "user-2"]}
        if name == "calculate_adp_from_picks":
            return _adp_result()
        raise AssertionError(f"Unexpected activity: {name}")

    async def _fake_execute_child_workflow(fn, params, **kwargs) -> dict:
        child_calls.append(params.user_id)
        # user-2 has insufficient picks
        skipped = params.user_id == "user-2"
        return _child_training_result(params.user_id, skipped=skipped)

    monkeypatch.setattr("workflows.league_model_training.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.league_model_training.workflow.execute_activity", _fake_execute_activity)
    monkeypatch.setattr("workflows.league_model_training.workflow.execute_child_workflow", _fake_execute_child_workflow)

    wf = LeagueModelTrainingWorkflow()
    result = await wf.run(LeagueModelTrainingWorkflowParams(league_id="league-1"))

    assert result["num_trained"] == 1
    assert result["num_skipped"] == 1


@pytest.mark.asyncio
async def test_league_model_training_exits_early_with_no_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no owners are found the workflow exits before ADP and child steps."""
    activity_calls: list = []
    child_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "get_league_team_owners":
            return {"owner_user_ids": []}
        raise AssertionError(f"Unexpected activity after early exit: {name}")

    async def _fake_execute_child_workflow(*args, **kwargs) -> dict:
        child_calls.append(True)
        raise AssertionError("Child workflow should not be called")

    monkeypatch.setattr("workflows.league_model_training.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.league_model_training.workflow.execute_activity", _fake_execute_activity)
    monkeypatch.setattr("workflows.league_model_training.workflow.execute_child_workflow", _fake_execute_child_workflow)

    wf = LeagueModelTrainingWorkflow()
    result = await wf.run(LeagueModelTrainingWorkflowParams(league_id="league-1"))

    assert result["num_owners"] == 0
    assert result["num_trained"] == 0
    assert result["owner_results"] == []
    assert "calculate_adp_from_picks" not in activity_calls
    assert len(child_calls) == 0
