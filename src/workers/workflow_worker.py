import asyncio
import os
import traceback
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    # Service/Client Managers
    from activities.clients.postgres_client import get_postgres_client_manager
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.pytorch_client import get_pytorch_model_manager
    # Data Collection Workflows
    from workflows.team_owner_data_collection import TeamOwnerDataCollectionWorkflow
    from workflows.league_data_collection import LeagueDataCollectionWorkflow
    from workflows.draft_data_collection import DraftDataCollectionWorkflow
    from workflows.player_data_collection import PlayerDataCollectionWorkflow
    from workflows.full_data_collection import FullDataCollectionWorkflow
    # Data Collection Activities
    from activities.draft.get_drafts import get_league_drafts
    from activities.draft.get_draft_picks import get_specific_draft_picks
    from activities.draft.get_traded_draft_picks import get_traded_draft_picks
    from activities.team_owner.get_roster import get_team_owner_rosters
    from activities.team_owner.get_data import get_team_owner_data
    from activities.league.get_data import get_league_data
    from activities.players.get_all_players import get_all_player_data
    # ML Activities
    from activities.ml.predictions.predict_player_pick import predict_owner_draft_pick, batch_predict_owner, get_player_features_from_db


async def main():
    """Entry point for the Temporal worker service.

    Connects to the Temporal server, registers workflows and activities, and
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
        sleeper = get_sleeper_client_manager()
        postgres = get_postgres_client_manager()
        postgres.create_all_tables()  # Only for development/testing - use Alembic migrations in production!
        pytorch_client = get_pytorch_model_manager()

        try:
            print(f"Starting Workflow Worker...")
            worker = Worker(
                client,
                task_queue=temporal_task_queue,
                workflows=[
                    TeamOwnerDataCollectionWorkflow,
                    LeagueDataCollectionWorkflow,
                    DraftDataCollectionWorkflow,
                    PlayerDataCollectionWorkflow,
                    FullDataCollectionWorkflow
                ],
                activities=[
                    get_league_data,
                    get_league_drafts,
                    get_specific_draft_picks,
                    get_traded_draft_picks,
                    get_team_owner_rosters, 
                    get_team_owner_data,
                    get_all_player_data,
                    predict_owner_draft_pick,
                    batch_predict_owner,
                    get_player_features_from_db,
                ],
            )
            print("Workflow Worker started.")

            await worker.run()
        except Exception as e:
            print(f"Workflow Worker failed to start: {e}")
        finally:
            # Ensure clients used are closed
            pytorch_client.close()
            await sleeper.close()
            postgres.drop_all_tables()  # Only for development/testing - remove in production!
            await postgres.close()
            print("Workflow Worker has shut down.")

    except KeyboardInterrupt:
        print("Workflow Worker stopped by user")
    except Exception as e:
        print(f"Workflow Worker error: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(main())