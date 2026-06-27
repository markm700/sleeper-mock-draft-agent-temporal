import pytest

from workflows.mock_draft_simulation import (
    MockDraftSimulationWorkflow,
    MockDraftSimulationWorkflowParams,
)


class MockWorkflowInfo:
    run_id = "test-run-id-abcd"


def _fake_workflow_info() -> MockWorkflowInfo:
    return MockWorkflowInfo()


def _models_result(user_ids: list) -> dict:
    return {
        "models": [{"model_name": f"owner_{uid}_league-1_v1"} for uid in user_ids],
        "num_models": len(user_ids),
    }


def _adp_result() -> dict:
    return {
        "adp_data": {"p1": {"adp": 1.0, "std_dev": 0.5, "times_drafted": 5}},
        "num_players": 1,
        "num_picks": 10,
        "num_drafts": 2,
    }


def _draft_context_result(user_ids: list, num_rounds: int = 1) -> dict:
    num_teams = len(user_ids)
    # snake draft order: round 1 forward, round 2 reverse
    draft_order = []
    for r in range(1, num_rounds + 1):
        order = user_ids if r % 2 == 1 else list(reversed(user_ids))
        for slot, uid in enumerate(order, 1):
            draft_order.append({
                "user_id": uid,
                "display_name": f"Owner {uid}",
                "draft_slot": slot,
                "pick_no": (r - 1) * num_teams + slot,
                "round": r,
            })
    return {
        "draft_order": draft_order,
        "candidate_players": [
            {"player_id": f"p{i}", "full_name": f"Player {i}", "position": "RB",
             "adp": float(i + 1), "adp_std": 0.5, "times_drafted": 5}
            for i in range(num_teams * num_rounds + 5)
        ],
        "owner_profiles": {uid: {"adp_deviation": 0.5} for uid in user_ids},
        "num_teams": num_teams,
    }


def _prediction_result(player_id: str) -> dict:
    return {
        "predictions": [{"player_id": player_id, "confidence": 0.9}],
        "top_3_predictions": [{"player_id": player_id}],
        "personality_influence_used": 0.5,
        "model_name": f"owner_{player_id}_league-1_v1",
        "num_candidates": 5,
    }


@pytest.mark.asyncio
async def test_mock_draft_simulation_runs_full_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2-team 2-round draft produces 4 picks, one prediction per pick."""
    user_ids = ["user-1", "user-2"]
    activity_calls: list = []
    pick_counter = [0]

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "list_models":
            return _models_result(user_ids)
        if name == "calculate_adp_from_picks":
            return _adp_result()
        if name == "get_draft_simulation_context":
            return _draft_context_result(user_ids, num_rounds=2)
        if name == "batch_predict_owner":
            idx = pick_counter[0]
            pick_counter[0] += 1
            return _prediction_result(f"p{idx}")
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.execute_activity", _fake_execute_activity)

    wf = MockDraftSimulationWorkflow()
    params = MockDraftSimulationWorkflowParams(league_id="league-1", num_rounds=2)
    result = await wf.run(params)

    assert result["num_picks"] == 4
    assert result["num_rounds"] == 2
    assert len(result["draft_board"]) == 4

    # Each pick should record user_id, player info, and the model used
    for entry in result["draft_board"]:
        assert "user_id" in entry
        assert "player_id" in entry
        assert "model_used" in entry

    # One batch_predict_owner call per pick
    prediction_calls = [n for n in activity_calls if n == "batch_predict_owner"]
    assert len(prediction_calls) == 4


@pytest.mark.asyncio
async def test_mock_draft_simulation_exits_when_no_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no trained models exist the workflow returns an error and does not draft."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "list_models":
            return {"models": [], "num_models": 0}
        raise AssertionError(f"Unexpected activity after early exit: {name}")

    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.execute_activity", _fake_execute_activity)

    wf = MockDraftSimulationWorkflow()
    result = await wf.run(MockDraftSimulationWorkflowParams(league_id="league-1"))

    assert result["draft_board"] == []
    assert result["num_picks"] == 0
    assert result.get("error") == "no_trained_models"
    assert "calculate_adp_from_picks" not in activity_calls


@pytest.mark.asyncio
async def test_mock_draft_simulation_summary_by_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """summary_by_owner groups picks correctly per owner."""
    user_ids = ["user-1", "user-2"]
    pick_counter = [0]

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        if name == "list_models":
            return _models_result(user_ids)
        if name == "calculate_adp_from_picks":
            return _adp_result()
        if name == "get_draft_simulation_context":
            return _draft_context_result(user_ids, num_rounds=1)
        if name == "batch_predict_owner":
            idx = pick_counter[0]
            pick_counter[0] += 1
            return _prediction_result(f"p{idx}")
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.execute_activity", _fake_execute_activity)

    wf = MockDraftSimulationWorkflow()
    result = await wf.run(MockDraftSimulationWorkflowParams(league_id="league-1", num_rounds=1))

    summary = result["summary_by_owner"]
    assert set(summary.keys()) == {"user-1", "user-2"}
    # 2 teams × 1 round = 1 pick per owner
    assert len(summary["user-1"]["picks"]) == 1
    assert len(summary["user-2"]["picks"]) == 1


@pytest.mark.asyncio
async def test_mock_draft_simulation_no_model_owner_uses_adp_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner without a trained model falls back to ADP (no batch_predict_owner call)."""
    # Only user-1 has a model; user-2 does not
    user_ids = ["user-1", "user-2"]
    prediction_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        if name == "list_models":
            return {"models": [{"model_name": "owner_user-1_league-1_v1"}], "num_models": 1}
        if name == "calculate_adp_from_picks":
            return _adp_result()
        if name == "get_draft_simulation_context":
            return _draft_context_result(user_ids, num_rounds=1)
        if name == "batch_predict_owner":
            prediction_calls.append(args[0].user_id if args else None)
            return _prediction_result("p0")
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.mock_draft_simulation.workflow.execute_activity", _fake_execute_activity)

    wf = MockDraftSimulationWorkflow()
    result = await wf.run(MockDraftSimulationWorkflowParams(league_id="league-1", num_rounds=1))

    # Only 1 of the 2 picks should have used the model
    assert len(prediction_calls) == 1
    assert prediction_calls[0] == "user-1"

    # The user-2 pick still appears in the board, but via ADP fallback
    user2_picks = [p for p in result["draft_board"] if p["user_id"] == "user-2"]
    assert len(user2_picks) == 1
    assert user2_picks[0]["model_used"] == "adp_fallback"
