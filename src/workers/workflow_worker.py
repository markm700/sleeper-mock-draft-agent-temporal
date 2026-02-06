import asyncio
import os
import traceback
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from workflows.team_owner_data_collection import TeamOwnerDataCollectionWorkflow
    from activities.team_owner.get_roster import get_team_owner_rosters
    from activities.team_owner.get_data import get_team_owner_data


async def main():
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

        try:
            print(f"Starting Workflow Worker...")
            worker = Worker(
                client,
                task_queue=temporal_task_queue,
                workflows=[TeamOwnerDataCollectionWorkflow],
                activities=[get_team_owner_rosters, get_team_owner_data],
            )
            print("Workflow Worker started.")

            await worker.run()
        except Exception as e:
            print(f"Workflow Worker failed to start: {e}")
        finally:
            # Ensure clients used are closed
            sleeper.close()
            print("Workflow Worker has shut down.")

    except KeyboardInterrupt:
        print("Workflow Worker stopped by user")
    except Exception as e:
        print(f"Workflow Worker error: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(main())