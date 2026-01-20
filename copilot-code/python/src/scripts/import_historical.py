"""Import historical data script"""
import logging
from src.services.data_import_service import data_import_service
from src.config import config

logger = logging.getLogger(__name__)


def main():
    """Main entry point for import script"""
    import sys
    
    username = config.sleeper['username'] or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not username:
        logger.error('Username required')
        print('Usage: python -m src.scripts.import_historical <username>')
        print('Or set SLEEPER_USERNAME in .env')
        sys.exit(1)
    
    try:
        data_import_service.import_historical_data(username)
    except Exception as error:
        logger.error('Import failed', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
