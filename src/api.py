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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Manage Temporal client lifecycle
    ## Startup - persistent client connection
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
    connection_check()
    return {
        "fastapi_status": "running",
        "temporal_connected": True
    }

@app.get("/healthz")
async def healthz():
    return {
        "fastapi_status": "running"
    }

@app.get("/healthz/temporal-worker-service/status")
async def healthz_temporal_worker_service_status():
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
            id=f"workflow-{workflow_name}-{username}-{os.urandom(4).hex()}",
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
    # Debug endpoint to check worker configuration
    if not app.state.temporal_client:
        raise HTTPException(status_code=503, detail=CONNECTION_DETAIL)
    return True