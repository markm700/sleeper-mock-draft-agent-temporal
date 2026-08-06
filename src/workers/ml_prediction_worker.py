import asyncio
import os
import traceback
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow

from observability.logging_config import setup_logging

with workflow.unsafe.imports_passed_through():
    # Client Managers
    from activities.clients.ml_client import get_ml_model_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    # ML Workflows
    from workflows.model_prediction import ModelPredictionWorkflow
    from workflows.mock_draft_simulation import MockDraftSimulationWorkflow
    # ML Activities
    from activities.ml.models.manage_model import list_models
    from activities.ml.predictions.predict_player_pick import predict_owner_draft_pick, batch_predict_owner, get_player_features_from_db
    from activities.ml.predictions.get_draft_simulation_context import get_draft_simulation_context
    from activities.ml.calculate_adp import calculate_adp_from_picks


async def main():
    """Entry point for the ML Temporal worker service.

    Connects to the Temporal server, registers ML workflows and activities, and
    runs the worker event loop.
    """
    try:
        setup_logging()
        temporal_host: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
        temporal_namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
        temporal_task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "example-ml-prediction-task-queue")

        print(f"Connecting to Temporal server {temporal_host} namespace={temporal_namespace} ...")
        client = await Client.connect(
            temporal_host,
            namespace=temporal_namespace
        )
        print(f"Connected to Temporal server!")

        # Initialize shared clients
        print("Initializing workflow and activity shared clients...")
        ml_client = get_ml_model_manager()
        postgres_client = get_postgres_client_manager()
        
        try:
            print(f"Starting ML Prediction Worker...")
            worker = Worker(
                client,
                task_queue=temporal_task_queue,
                max_concurrent_activities=30,
                max_concurrent_workflow_tasks=100,
                workflows=[
                    ModelPredictionWorkflow,
                    MockDraftSimulationWorkflow,
                ],
                activities=[
                    get_player_features_from_db,
                    predict_owner_draft_pick,
                    batch_predict_owner,
                    list_models,
                    calculate_adp_from_picks,
                    get_draft_simulation_context,
                ],
            )
            print("ML Prediction Worker started.")

            await worker.run()
        except Exception as e:
            print(f"ML Prediction Worker failed to start: {e}")
        finally:
            ## Shutdown - close shared clients
            print("Closing shared clients...")
            if ml_client:
                ml_client.close()
                print("ML Model client closed.")
            if postgres_client:
                await postgres_client.close()
                print("Postgres client closed.")
            print("ML Prediction Worker has shut down.")

    except KeyboardInterrupt:
        print("ML Prediction Worker stopped by user")
    except Exception as e:
        print(f"ML Prediction Worker error: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
