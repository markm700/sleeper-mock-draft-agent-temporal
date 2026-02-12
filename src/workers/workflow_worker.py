import asyncio
import os
import traceback
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.postgres_client import get_postgres_client_manager
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.sleeper_client_credential import get_postgres_client_manager
    from workflows.team_owner_data_collection import TeamOwnerDataCollectionWorkflow
    from workflows.league_data_collection import LeagueDataCollectionWorkflow
    from workflows.full_data_collection import FullDataCollectionWorkflow
    from activities.draft.get_drafts import get_league_drafts
    from activities.draft.get_draft_picks import get_specific_draft_picks
    from activities.draft.get_traded_draft_picks import get_traded_draft_picks
    from activities.team_owner.get_roster import get_team_owner_rosters
    from activities.team_owner.get_data import get_team_owner_data
    from activities.league.get_data import get_league_data


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

        try:
            print(f"Starting Workflow Worker...")
            worker = Worker(
                client,
                task_queue=temporal_task_queue,
                workflows=[
                    TeamOwnerDataCollectionWorkflow,
                    LeagueDataCollectionWorkflow,
                    DraftDataCollectionWorkflow,
                    FullDataCollectionWorkflow
                ],
                activities=[
                    get_league_data,
                    get_league_drafts,
                    get_specific_draft_picks,
                    get_traded_draft_picks,
                    get_team_owner_rosters, 
                    get_team_owner_data
                ],
            )
            print("Workflow Worker started.")

            await worker.run()
        except Exception as e:
            print(f"Workflow Worker failed to start: {e}")
        finally:
            # Ensure clients used are closed
            await sleeper.close()
            await postgres.close()
            await sleeper.close()
            await postgres.close()
            print("Workflow Worker has shut down.")

    except KeyboardInterrupt:
        print("Workflow Worker stopped by user")
    except Exception as e:
        print(f"Workflow Worker error: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(main())