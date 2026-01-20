"""Run analysis script"""
import logging
from src.services.analysis_service import analysis_service

logger = logging.getLogger(__name__)


def main():
    """Main entry point for analysis script"""
    try:
        analysis_service.run_analysis()
    except Exception as error:
        logger.error('Analysis failed', exc_info=True)
        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()
