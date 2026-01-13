#!/usr/bin/env python3

import asyncio
import sys
from src.services.data_import_service import data_import_service
from src.config import config


async def main():
    username = config.SLEEPER_USERNAME or (sys.argv[1] if len(sys.argv) > 1 else None)

    if not username:
        print("Usage: python -m src.scripts.import_historical <username>")
        print("Or set SLEEPER_USERNAME in .env")
        sys.exit(1)

    try:
        await data_import_service.import_historical_data(username)
    except Exception as error:
        print(f"Import failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
