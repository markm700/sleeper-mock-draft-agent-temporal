import os
from contextlib import asynccontextmanager
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from temporalio.client import Client, WorkflowHandle

temporal_client = None
CONNECTION_DETAIL = "Temporal server not connected"

temporal_host: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
temporal_namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
temporal_task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "task-queue")


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
    # Startup - persistent client connection
    print(f"Connecting to self-hosted Temporal at {temporal_host}...")
    app.state.temporal_client = await Client.connect(
        temporal_host,
        namespace=temporal_namespace,
    )
    print(f"Connected to Temporal: {app.state.temporal_client}")
    
    yield  # App running
    
    ## Shutdown - close client
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

@app.get("/healthz/temporal-worker-service/status")
async def healthz_temporal_worker_service_status():
    """Report Temporal worker service connection details and status."""
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

# Helper Functions
def connection_check():
    """Ensure the Temporal client is connected before handling a request."""
    if not app.state.temporal_client:
        raise HTTPException(status_code=503, detail=CONNECTION_DETAIL)
    return True