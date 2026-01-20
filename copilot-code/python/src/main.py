"""Main application entry point"""
import logging
from src.database.db import db
from src.config import config

logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    logger.info('Sleeper Mock Draft Agent v1.0.0\n')
    
    try:
        # Test database connection
        db.initialize()
        
        logger.info('\nReady for draft analysis!')
        logger.info('Run "python -m src.scripts.import_historical" to import data')
        logger.info('Run "python -m src.scripts.run_analysis" to generate predictions')
        
    except Exception as error:
        logger.error('Fatal error:', exc_info=True)
        raise


if __name__ == '__main__':
    main()
