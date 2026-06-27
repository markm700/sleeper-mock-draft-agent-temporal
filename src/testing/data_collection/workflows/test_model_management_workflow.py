import pytest

from workflows.model_management import ModelManagementWorkflow, ModelManagementWorkflowParams


class MockWorkflowInfo:
    run_id = "test-run-id-abcd"


def _fake_workflow_info() -> MockWorkflowInfo:
    return MockWorkflowInfo()


@pytest.mark.asyncio
async def test_model_management_status_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """status action calls get_model_status and returns its result."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "get_model_status":
            return {"exists_on_disk": True, "cached_in_memory": False, "model_name": "model_v1"}
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_management.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_management.workflow.execute_activity", _fake_execute_activity)

    wf = ModelManagementWorkflow()
    result = await wf.run(ModelManagementWorkflowParams(model_name="model_v1", action="status"))

    assert len(result["activity_data"]) == 1
    assert result["activity_data"][0]["activity"] == "get_model_status"
    assert result["activity_data"][0]["result"]["exists_on_disk"] is True

    name, args = activity_calls[0]
    assert name == "get_model_status"
    assert args[0].model_name == "model_v1"


@pytest.mark.asyncio
async def test_model_management_build_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build action calls build_owner_model with overwrite=False."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "build_owner_model":
            return {"created": True, "model_type": "TeamOwnerDraftModel", "model_path": "/models/m.joblib"}
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_management.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_management.workflow.execute_activity", _fake_execute_activity)

    wf = ModelManagementWorkflow()
    result = await wf.run(ModelManagementWorkflowParams(model_name="model_v1", action="build"))

    assert result["activity_data"][0]["activity"] == "build_owner_model"
    assert result["activity_data"][0]["result"]["created"] is True

    _, args = activity_calls[0]
    assert args[0].overwrite is False


@pytest.mark.asyncio
async def test_model_management_rebuild_action_sets_overwrite_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rebuild action calls build_owner_model with overwrite=True."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "build_owner_model":
            return {"created": True, "model_type": "TeamOwnerDraftModel", "model_path": "/models/m.joblib"}
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_management.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_management.workflow.execute_activity", _fake_execute_activity)

    wf = ModelManagementWorkflow()
    await wf.run(ModelManagementWorkflowParams(model_name="model_v1", action="rebuild"))

    _, args = activity_calls[0]
    assert args[0].overwrite is True


@pytest.mark.asyncio
async def test_model_management_list_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """list action calls list_models and records num_models."""
    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        if name == "list_models":
            return {"models": [{"model_name": "model_v1"}], "num_models": 1}
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_management.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_management.workflow.execute_activity", _fake_execute_activity)

    wf = ModelManagementWorkflow()
    result = await wf.run(ModelManagementWorkflowParams(model_name="model_v1", action="list"))

    assert result["activity_data"][0]["activity"] == "list_models"
    assert result["activity_data"][0]["result"]["num_models"] == 1


@pytest.mark.asyncio
async def test_model_management_delete_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """delete action calls delete_model with the correct model name."""
    activity_calls: list = []

    async def _fake_execute_activity(fn, *args, **kwargs) -> dict:
        name = getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "delete_model":
            return {"deleted_from_disk": True, "evicted_from_cache": True, "model_name": "model_v1"}
        raise AssertionError(f"Unexpected activity: {name}")

    monkeypatch.setattr("workflows.model_management.workflow.info", _fake_workflow_info)
    monkeypatch.setattr("workflows.model_management.workflow.execute_activity", _fake_execute_activity)

    wf = ModelManagementWorkflow()
    result = await wf.run(ModelManagementWorkflowParams(model_name="model_v1", action="delete"))

    assert result["activity_data"][0]["activity"] == "delete_model"
    _, args = activity_calls[0]
    assert args[0].model_name == "model_v1"


@pytest.mark.asyncio
async def test_model_management_invalid_action_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown action raises ValueError without calling any activity."""
    monkeypatch.setattr("workflows.model_management.workflow.info", _fake_workflow_info)
    monkeypatch.setattr(
        "workflows.model_management.workflow.execute_activity",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    wf = ModelManagementWorkflow()
    with pytest.raises(ValueError, match="Unknown action"):
        await wf.run(ModelManagementWorkflowParams(model_name="model_v1", action="frobnicate"))
