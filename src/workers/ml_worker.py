import asyncio
import os
import traceback
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    # Service/Client Managers
    from activities.clients.postgres_client import get_postgres_client_manager
    from activities.clients.ml_client import get_ml_model_manager
    # ML Workflows
    from workflows.model_management import ModelManagementWorkflow
    from workflows.model_training import ModelTrainingWorkflow
    from workflows.league_model_training import LeagueModelTrainingWorkflow
    from workflows.model_prediction import ModelPredictionWorkflow
    from workflows.mock_draft_simulation import MockDraftSimulationWorkflow
    # ML Activities
    from activities.ml.predictions.predict_player_pick import predict_owner_draft_pick, batch_predict_owner, get_player_features_from_db
    from activities.ml.predictions.get_draft_simulation_context import get_draft_simulation_context
    from activities.ml.calculate_adp import calculate_adp_from_picks
    from activities.ml.models.manage_model import build_owner_model, get_model_status, list_models, delete_model
    from activities.ml.training.prepare_training_data import prepare_owner_training_data
    from activities.ml.training.train_model import train_team_owner_model
    from activities.ml.get_league_team_owners import get_league_team_owners


async def main():
    """Entry point for the ML Temporal worker service.

    Connects to the Temporal server, registers ML workflows and activities, and
    runs the worker event loop.
    """
    try:
        temporal_host: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
        temporal_namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
        temporal_task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "task-queue-placeholder")

        print(f"Connecting to Temporal server {temporal_host} namespace={temporal_namespace} ...")
        client = await Client.connect(
            temporal_host,
            namespace=temporal_namespace
        )
        print(f"Connected to Temporal server!")

        # Initialize activity/workflow clients
        postgres = get_postgres_client_manager()
        ml_client = get_ml_model_manager()

        try:
            print(f"Starting ML Workflow Worker...")
            worker = Worker(
                client,
                task_queue=temporal_task_queue,
                workflows=[
                    ModelManagementWorkflow,
                    ModelTrainingWorkflow,
                    LeagueModelTrainingWorkflow,
                    ModelPredictionWorkflow,
                    MockDraftSimulationWorkflow,
                ],
                activities=[
                    predict_owner_draft_pick,
                    batch_predict_owner,
                    get_player_features_from_db,
                    calculate_adp_from_picks,
                    build_owner_model,
                    get_model_status,
                    list_models,
                    delete_model,
                    prepare_owner_training_data,
                    train_team_owner_model,
                    get_league_team_owners,
                    get_draft_simulation_context,
                ],
            )
            print("ML Workflow Worker started.")

            await worker.run()
        except Exception as e:
            print(f"ML Workflow Worker failed to start: {e}")
        finally:
            ml_client.close()
            await postgres.close()
            print("ML Workflow Worker has shut down.")

    except KeyboardInterrupt:
        print("ML Workflow Worker stopped by user")
    except Exception as e:
        print(f"ML Workflow Worker error: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
