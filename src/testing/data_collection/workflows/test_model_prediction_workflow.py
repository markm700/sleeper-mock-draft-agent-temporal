import pytest

from workflows.model_prediction import ModelPredictionWorkflow, ModelPredictionWorkflowParams


class MockWorkflowInfo:
    run_id = "test-run-id-abcd"


def _fake_workflow_info() -> MockWorkflowInfo:
    return MockWorkflowInfo()


def _fake_features_result(num_players: int = 2) -> dict:
    return {
        "player_features": [
            {
                "player_id": f"p{i}",
                "full_name": f"Player {i}",
                "position": "RB",
                "age": 25,
                "years_exp": 3,
                "adp": float(i + 1),
                "adp_std": 0.5,
                "times_drafted": 10,
            }
            for i in range(num_players)
        ],
        "num_players": num_players,
        "missing_players": 0,
    }


def _fake_prediction_result() -> dict:
    return {
        "predictions": {"top_prediction": {"player_id": "p0", "confidence": 0.8}},
        "top_3_predictions": [{"player_id": "p0"}, {"player_id": "p1"}],
        "model_name": "owner_u1_l1_v1",
        "num_candidates": 2,
        "personality_influence_used": 0.7,
    }


def _base_params(**overrides) -> ModelPredictionWorkflowParams:
    defaults = dict(
        model_name="owner_u1_l1_v1",
        user_id="user-1",
        player_ids=["p0", "p1"],
        draft_context={"pick_no": 5},
        owner_profile={"adp_deviation": 0.5},
    )
    defaults.update(overrides)
    return ModelPredictionWorkflowParams(**defaults)


@pytest.mark.asyncio
async def test_model_prediction_single_mode_calls_predict_owner_draft_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-batch mode calls predict_owner_draft_pick and returns ranked predictions."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "get_player_features_from_db":
            return _fake_features_result(2)
        if name == "predict_owner_draft_pick":
            return _fake_prediction_result()
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_prediction.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_prediction.workflow.execute_activity", _fake_execute_activity)

    wf = ModelPredictionWorkflow()
    result = await wf.run(_base_params(batch_mode=False))

    assert result["skipped"] is not True
    assert result["num_candidates"] == 2
    assert result["model_name"] == "owner_u1_l1_v1"
    assert "predictions" in result
    assert len(result["activity_data"]) == 2

    names = [name for name, _ in activity_calls]
    assert names == ["get_player_features_from_db", "predict_owner_draft_pick"]

    _, feat_args = activity_calls[0]
    assert feat_args[0].player_ids == ["p0", "p1"]

    _, pred_args = activity_calls[1]
    assert pred_args[0].user_id == "user-1"
    assert pred_args[0].model_name == "owner_u1_l1_v1"


@pytest.mark.asyncio
async def test_model_prediction_batch_mode_calls_batch_predict_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch mode calls batch_predict_owner instead of predict_owner_draft_pick."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "get_player_features_from_db":
            return _fake_features_result(2)
        if name == "batch_predict_owner":
            return _fake_prediction_result()
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_prediction.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_prediction.workflow.execute_activity", _fake_execute_activity)

    wf = ModelPredictionWorkflow()
    result = await wf.run(_base_params(batch_mode=True))

    assert "predict_owner_draft_pick" not in activity_calls
    assert "batch_predict_owner" in activity_calls
    assert result["num_candidates"] == 2


@pytest.mark.asyncio
async def test_model_prediction_skips_when_no_player_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workflow exits early when feature fetch returns empty list."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "get_player_features_from_db":
            return {"player_features": [], "num_players": 0, "missing_players": 2}
        raise AssertionError(f"Unexpected activity after early exit: {name}")

    monkeypatch.setattr("workflows.model_prediction.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_prediction.workflow.execute_activity", _fake_execute_activity)

    wf = ModelPredictionWorkflow()
    result = await wf.run(_base_params())

    assert result["skipped"] is True
    assert result["reason"] == "no_player_features"
    assert result["num_candidates"] == 0
    assert "predict_owner_draft_pick" not in activity_calls
    assert "batch_predict_owner" not in activity_calls
