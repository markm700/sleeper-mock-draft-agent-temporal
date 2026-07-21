"""
Langfuse client manager for tracing and evaluations.

Provides Langfuse helper functions for workflow/activity execution traces, 
log LLM calls, and record evaluation scores for observability.
"""

import asyncio
import langfuse
import logging
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

class LangfuseClientManager:
    """Async client manager for the Langfuse python package.
    
        Behaves as a singleton to ensure a single shared instance of the Langfuse client across the application.
        Essentially acts as a wrapper for the langfuse python package.
        Docs Link: https://python.reference.langfuse.com/langfuse
    """

    def __init__(self):
        """Initialize the Langfuse client."""
        self._client: Optional[langfuse.Langfuse] = None

    @property
    def client(self) -> langfuse.Langfuse:
        """Get or create the shared Langfuse instance. langfuse.get_client() is already a singleton instance."""
        if self._client is None:
            self._client = langfuse.get_client()
        self._connection_health_check()
        return self._client

    def _connection_health_check(self) -> bool:
        """Check the health of the Langfuse client."""
        try:
            # Verify connection
            self.client.health_check()
            logger.info("Langfuse client is authenticated and ready!")
            return True
        except Exception as e:
            logger.error(f"Langfuse client health check failed (check credentials and host): {e}")
            return False
    
    def traced_activity(self, name=None, **observe_kwargs):
        """Wraps langfuse's @observe with project-specific defaults, adds better logging."""
        def decorator(func):
            lf_observe = self.client.observe(
                name=name or func.__name__,
                capture_input=True,
                capture_output=True,
                **observe_kwargs,
            )(func)

            if asyncio.iscoroutinefunction(func):
                """
                Temporal checks whether an activity is a coroutine. 
                Wrapping async functions with regular decorators would make this fail, need the async decorator.
                """
                @wraps(lf_observe)
                async def async_wrapper(*args, **kwargs):
                    try:
                        return await lf_observe(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Langfuse Error in async traced activity '{func.__name__}': {e}")
                        raise
                return async_wrapper
            else:
                @wraps(lf_observe)
                def sync_wrapper(*args, **kwargs):
                    try:
                        return lf_observe(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Langfuse Error in traced activity '{func.__name__}': {e}")
                        raise
                return sync_wrapper
        return decorator

    def close(self) -> None:
        """
        Flush the Langfuse client.
        
        Call this when shutting down the application to cleanly close all connections.
        """
        self.client.shutdown()
        logger.info("Flushed abd shut down Langfuse client")

# Module-level singleton instance for reuse across activities
_langfuse_client_instance: Optional[LangfuseClientManager] = None

def get_langfuse_client_manager() -> LangfuseClientManager:
    """Get the single Langfuse client manager instance."""
    global _langfuse_client_instance
    if _langfuse_client_instance is None:
        _langfuse_client_instance = LangfuseClientManager()
    return _langfuse_client_instance