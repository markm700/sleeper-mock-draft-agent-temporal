import os
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, Dict, List, Final
from fastapi import FastAPI, HTTPException, Query
from temporalio.client import Client, WorkflowHandle

from .observability.logging_config import setup_logging

temporal_client = None
CONNECTION_DETAIL: Final[str] = "Temporal server not connected"

temporal_host: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
temporal_namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
temporal_task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "task-queue")
temporal_ml_task_queue: str = os.getenv("TEMPORAL_ML_TASK_QUEUE", "task-queue-ml")
temporal_ml_prediction_task_queue: str = os.getenv("TEMPORAL_ML_PREDICTION_TASK_QUEUE", "task-queue-ml-prediction")


def _safe_slug(text: str | None) -> str:
    """Create a simple, deterministic slug for IDs without slugify.

    Only uses ASCII letters/digits and dashes so it's safe for workflow IDs.
    """

    if not text:
        return "value"

    cleaned = []
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch.lower())
        else:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    return slug or "value"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Temporal client lifecycle for the FastAPI application."""
    # Startup - configure logging, then open a persistent client connection
    setup_logging()
    print(f"Connecting to self-hosted Temporal at {temporal_host}...")
    app.state.temporal_client = await Client.connect(
        temporal_host,
        namespace=temporal_namespace,
    )
    print(f"Connected to Temporal: {app.state.temporal_client}")

    yield  # App running

    ## Shutdown - close Temporal client
    print("Disconnecting from Temporal...")
    if app.state.temporal_client:
        await app.state.temporal_client.close()
        print("Disconnected.")

app = FastAPI(lifespan=lifespan)

# Basic/Health Checks
@app.get("/")
async def basic_get():
    """Return basic service and Temporal connectivity status."""
    connection_check()
    return {
        "fastapi_status": "running",
        "temporal_connected": True
    }

@app.get("/healthz")
async def healthz():
    """Liveness probe endpoint for the FastAPI service."""
    return {
        "fastapi_status": "running"
    }


@app.get("/healthz/data-collection-worker-service/status")
async def healthz_data_collection_worker_service_status():
    """Report data collection worker service connection details and status."""
    connection_check()
    return {
        "temporal_host": temporal_host,
        "namespace": temporal_namespace,
        "task_queue": temporal_task_queue,
        "client_connected": app.state.temporal_client is not None
    }


# Workflow Invocations
@app.post("/team-owner-data-collection/run")
async def invoke_team_owner_data_workflow(username: str = os.getenv("SLEEPER_USERNAME"), league_name: str = os.getenv("SLEEPER_LEAGUE_NAME")) -> Dict[str, Any]:
    """Invoke the team-owner-data-collection workflow for a given user/league."""
    connection_check()
    workflow_name = "team-owner-data-collection"
    try:
        params = {
            "username": username,
            "league_name": league_name
        }
        # Start the workflow with the given name and params
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{username}-{_safe_slug(league_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")

@app.post("/player-data-collection/run")
async def invoke_player_data_workflow() -> Dict[str, Any]:
    """Invoke the player-data-collection workflow for a given user/league."""
    connection_check()
    workflow_name = "player-data-collection"
    try:
        # Start the workflow with the given name and params
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[],
            id=f"workflow-{_safe_slug(workflow_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")
    
@app.post("/full-data-collection/run")
async def invoke_full_data_workflow(username: str = os.getenv("SLEEPER_USERNAME"), league_name: str = os.getenv("SLEEPER_LEAGUE_NAME")) -> Dict[str, Any]:
    """Invoke the full-data-collection workflow for a given user/league."""
    connection_check()
    workflow_name = "full-data-collection"
    try:
        params = {
            "username": username,
            "league_name": league_name
        }
        # Start the workflow with the given name and params
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{username}-{_safe_slug(league_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")

class ModelManagementWorkflowAction(str, Enum):
    BUILD = "build"
    REBUILD = "rebuild"
    STATUS = "status"
    LIST = "list"
    DELETE = "delete"
    
@app.post("/model-management/run")
async def invoke_model_management_workflow(model_name: str, action: ModelManagementWorkflowAction = ModelManagementWorkflowAction.STATUS) -> Dict[str, Any]:
    """Invoke the model-management workflow to build, rebuild, or check status of a model."""
    connection_check()
    workflow_name = "model-management"
    try:
        params = {
            "model_name": model_name,
            "action": action.value,
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{_safe_slug(model_name)}-{_safe_slug(action)}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")

@app.post("/model-training/run")
async def invoke_model_training_workflow(
    league_id: str,
    user_id: str,
    model_name: str = "",
    season: str | None = None,
    num_boost_round: int = 100,
    learning_rate: float = 0.05,
    rebuild_model: bool = False,
) -> Dict[str, Any]:
    """Invoke the model-training workflow to train a team owner draft prediction model."""
    connection_check()
    workflow_name = "model-training"
    try:
        params = {
            "league_id": league_id,
            "user_id": user_id,
            "model_name": model_name,
            "season": season,
            "num_boost_round": num_boost_round,
            "learning_rate": learning_rate,
            "rebuild_model": rebuild_model,
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{user_id}-{league_id}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")


@app.post("/league-model-training/run")
async def invoke_league_model_training_workflow(
    league_id: str,
    season: str | None = None,
    num_boost_round: int = 100,
    learning_rate: float = 0.05,
    rebuild_models: bool = False,
    min_picks_required: int = 10,
    additional_league_ids: List[str] | None = Query(None),
) -> Dict[str, Any]:
    """Invoke the league-model-training workflow to train models for all team owners in a league."""
    connection_check()
    workflow_name = "league-model-training"
    try:
        params = {
            "league_id": league_id,
            "season": season,
            "num_boost_round": num_boost_round,
            "learning_rate": learning_rate,
            "rebuild_models": rebuild_models,
            "min_picks_required": min_picks_required,
            "additional_league_ids": additional_league_ids,
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{league_id}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")


# Model Management Convenience Endpoints

@app.get("/models")
async def list_models() -> Dict[str, Any]:
    """List all available models on disk via the model-management workflow."""
    connection_check()
    workflow_name = "model-management"
    try:
        params = {
            "model_name": "",
            "action": "list",
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-list-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")


@app.get("/models/{model_name}/status")
async def get_model_status(model_name: str) -> Dict[str, Any]:
    """Get the status of a specific model via the model-management workflow."""
    connection_check()
    workflow_name = "model-management"
    try:
        params = {
            "model_name": model_name,
            "action": "status",
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-status-{_safe_slug(model_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model status: {e}")


@app.delete("/models/{model_name}")
async def delete_model(model_name: str) -> Dict[str, Any]:
    """Delete a model from disk and cache via the model-management workflow."""
    connection_check()
    workflow_name = "model-management"
    try:
        params = {
            "model_name": model_name,
            "action": "delete",
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-delete-{_safe_slug(model_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {e}")


@app.post("/models/{model_name}/build")
async def build_model(model_name: str) -> Dict[str, Any]:
    """Build a new model (skip if already exists) via the model-management workflow."""
    connection_check()
    workflow_name = "model-management"
    try:
        params = {
            "model_name": model_name,
            "action": "build",
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-build-{_safe_slug(model_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build model: {e}")


@app.post("/models/{model_name}/rebuild")
async def rebuild_model(model_name: str) -> Dict[str, Any]:
    """Force-rebuild a model from scratch via the model-management workflow."""
    connection_check()
    workflow_name = "model-management"
    try:
        params = {
            "model_name": model_name,
            "action": "rebuild",
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-rebuild-{_safe_slug(model_name)}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild model: {e}")


# Mock Draft Simulation Endpoint

@app.post("/mock-draft-simulation/run")
async def invoke_mock_draft_simulation_workflow(
    league_id: str,
    additional_league_ids: List[str] | None = Query(None),
    num_rounds: int = 15,
    draft_type: str = "snake",
    personality_influence_scale: float | None = None,
) -> Dict[str, Any]:
    """Invoke the mock-draft-simulation workflow to simulate a full draft using trained models."""
    connection_check()
    workflow_name = "mock-draft-simulation"
    try:
        params = {
            "league_id": league_id,
            "additional_league_ids": additional_league_ids,
            "num_rounds": num_rounds,
            "draft_type": draft_type,
            "personality_influence_scale": personality_influence_scale,
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{league_id}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_prediction_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start mock draft simulation: {e}")


# Model Prediction Endpoint

@app.post("/model-prediction/run")
async def invoke_model_prediction_workflow(
    model_name: str,
    user_id: str,
    player_ids: List[str],
    draft_context: Dict[str, Any],
    owner_profile: Dict[str, Any],
    personality_influence_scale: float | None = None,
    batch_mode: bool = False,
) -> Dict[str, Any]:
    """Invoke the model-prediction workflow to score candidate players for a team owner."""
    connection_check()
    workflow_name = "model-prediction"
    try:
        params = {
            "model_name": model_name,
            "user_id": user_id,
            "player_ids": player_ids,
            "draft_context": draft_context,
            "owner_profile": owner_profile,
            "personality_influence_scale": personality_influence_scale,
            "batch_mode": batch_mode,
        }
        wf: WorkflowHandle = await app.state.temporal_client.start_workflow(
            workflow_name,
            args=[params],
            id=f"workflow-{_safe_slug(workflow_name)}-{_safe_slug(model_name)}-{user_id}-{os.urandom(4).hex()}",
            task_queue=temporal_ml_prediction_task_queue,
        )
        wf_result = await wf.result()

        return {
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "result": wf_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start prediction workflow: {e}")


# Helper Functions
def connection_check():
    """Ensure the Temporal client is connected before handling a request."""
    if not app.state.temporal_client:
        raise HTTPException(status_code=503, detail=CONNECTION_DETAIL)
    return True