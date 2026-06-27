import pytest

from workflows.model_training import ModelTrainingWorkflow, ModelTrainingWorkflowParams


class MockWorkflowInfo:
    run_id = "test-run-id-abcd"


def _fake_workflow_info() -> MockWorkflowInfo:
    return MockWorkflowInfo()


def _adp_result() -> dict:
    return {
        "adp_data": {"player_1": {"adp": 1.0, "std_dev": 0.5, "times_drafted": 10}},
        "num_players": 1,
        "num_picks": 10,
        "num_drafts": 5,
    }


def _training_data_result(num_samples: int = 3) -> dict:
    return {
        "training_samples": [
            {
                "pick_no": i,
                "round": 1,
                "candidate_features": [[0.1] * 11],
                "context": [0.0] * 8,
                "target_idx": 0,
                "draft_id": "draft_1",
            }
            for i in range(num_samples)
        ],
        "owner_profile": [0.0] * 26,
        "personality_trait": "contrarian",
        "num_samples": num_samples,
        "user_id": "user-1",
        "league_id": "league-1",
        "season": None,
    }


@pytest.mark.asyncio
async def test_model_training_runs_all_four_activities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full happy path: ADP → prepare → build → train, returns model metadata."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args, kwargs))
        if name == "calculate_adp_from_picks":
            return _adp_result()
        if name == "prepare_owner_training_data":
            return _training_data_result(3)
        if name == "build_owner_model":
            return {"created": True, "model_type": "TeamOwnerDraftModel", "model_path": "/models/m.joblib"}
        if name == "train_team_owner_model":
            return {
                "model_name": "owner_user-1_league-1_v1",
                "model_path": "/models/m.joblib",
                "num_boost_round": 100,
                "num_samples": 3,
                "num_query_groups": 3,
            }
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_training.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_training.workflow.execute_activity", _fake_execute_activity)

    wf = ModelTrainingWorkflow()
    params = ModelTrainingWorkflowParams(league_id="league-1", user_id="user-1")
    result = await wf.run(params)

    assert result["skipped"] is False
    assert result["model_name"] == "owner_user-1_league-1_v1"
    assert "model_path" in result
    assert result["num_samples"] == 3
    assert len(activity_calls) == 4
    assert [name for name, _, _ in activity_calls] == [
        "calculate_adp_from_picks",
        "prepare_owner_training_data",
        "build_owner_model",
        "train_team_owner_model",
    ]

    # Verify prepare step receives ADP data
    _, prepare_args, _ = activity_calls[1]
    assert prepare_args[0].adp_data == _adp_result()["adp_data"]

    # Verify train step receives personality trait from training data
    _, train_args, _ = activity_calls[3]
    assert train_args[0].personality_trait == "contrarian"


@pytest.mark.asyncio
async def test_model_training_skips_when_no_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When prepare returns 0 samples the workflow exits early and skips training."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "calculate_adp_from_picks":
            return _adp_result()
        if name == "prepare_owner_training_data":
            return _training_data_result(0)
        raise AssertionError(f"Unexpected activity after early exit: {name}")

    monkeypatch.setattr("workflows.model_training.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_training.workflow.execute_activity", _fake_execute_activity)

    wf = ModelTrainingWorkflow()
    params = ModelTrainingWorkflowParams(league_id="league-1", user_id="user-1")
    result = await wf.run(params)

    assert result["skipped"] is True
    assert result["reason"] == "insufficient_training_samples"
    assert "build_owner_model" not in activity_calls
    assert "train_team_owner_model" not in activity_calls


@pytest.mark.asyncio
async def test_model_training_uses_precomputed_adp_when_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When precomputed_adp_data is passed the ADP activity is skipped."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append(name)
        if name == "prepare_owner_training_data":
            return _training_data_result(2)
        if name == "build_owner_model":
            return {"created": False, "model_type": "TeamOwnerDraftModel", "model_path": "/models/m.joblib"}
        if name == "train_team_owner_model":
            return {
                "model_name": "owner_user-1_league-1_v1",
                "model_path": "/models/m.joblib",
                "num_boost_round": 50,
                "num_samples": 2,
                "num_query_groups": 2,
            }
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_training.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_training.workflow.execute_activity", _fake_execute_activity)

    wf = ModelTrainingWorkflow()
    params = ModelTrainingWorkflowParams(
        league_id="league-1",
        user_id="user-1",
        precomputed_adp_data=_adp_result(),
    )
    result = await wf.run(params)

    assert result["skipped"] is False
    assert "calculate_adp_from_picks" not in activity_calls
    assert activity_calls[0] == "prepare_owner_training_data"
