#!/usr/bin/env python3

import asyncio
import sys
from src.services.analysis_service import analysis_service


async def main():
    try:
        await analysis_service.run_analysis()
    except Exception as error:
        print(f"Analysis failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
