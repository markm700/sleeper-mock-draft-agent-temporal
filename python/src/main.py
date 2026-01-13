import asyncio
from src.database.db import db
from src.services.live_draft_service import live_draft_service


async def main():
    """
    Main entry point for the application
    Can be extended to include API server, CLI interface, etc.
    """
    print("Sleeper Mock Draft Agent v1.0.0\n")

    # Initialize database
    db.initialize()

    # Example: Get recommendations for a draft state
    # This would typically be called via API or CLI
    draft_state = {
        # ... draft state data
    }

    # Uncomment to test live draft service:
    # recommendations = await live_draft_service.get_recommendations(
    #     'username',
    #     draft_state,
    #     1
    # )
    # print(recommendations)

    print("\nReady for draft analysis!")
    print('Run "python -m src.scripts.import_historical" to import historical data')
    print('Run "python -m src.scripts.run_analysis" to generate predictions')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(f"Fatal error: {error}")
        exit(1)
