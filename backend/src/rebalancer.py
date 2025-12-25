"""
Rebalancer - Automated loop that executes the strategy.
Runs every hour (aligned with funding payments).
"""
import asyncio
from datetime import datetime
from typing import Optional
try:
    from .strategy import UnboundVaultStrategy
    from .config import settings
    from .starknet_client import auto_depositor
except ImportError:
    from src.strategy import UnboundVaultStrategy
    from src.config import settings
    from src.starknet_client import auto_depositor
import structlog

logger = structlog.get_logger()


class Rebalancer:
    """
    Automated rebalancing service.
    
    Runs the strategy at regular intervals (default: every hour).
    """
    
    def __init__(self, strategy: Optional[UnboundVaultStrategy] = None):
        self.strategy = strategy or UnboundVaultStrategy()
        self.interval = settings.rebalance_interval_seconds
        self.running = False
        self.iteration_count = 0
        self.last_action = None
        self.last_run = None
    
    async def run_once(self) -> dict:
        """Run a single iteration of the strategy."""
        self.iteration_count += 1
        self.last_run = datetime.now()
        
        logger.info(
            "Rebalancer iteration",
            iteration=self.iteration_count,
            time=self.last_run.isoformat()
        )
        
        try:
            result = await self.strategy.execute_strategy()
            self.last_action = result
            
            # Auto-sync NAV after strategy execution to reflect profits
            try:
                state = await self.strategy.get_state()
                print(f"📊 Current Equity for NAV Sync: ${state.equity:.2f}")
                await auto_depositor.sync_vault_nav(state.equity)
            except Exception as nav_e:
                logger.error("NAV sync failed", error=str(nav_e))
            
            logger.info(
                "Strategy executed and NAV synced",
                action=result.get("action"),
                iteration=self.iteration_count
            )
            
            return result
            
        except Exception as e:
            logger.error("Strategy execution failed", error=str(e))
            return {"action": "ERROR", "error": str(e)}
    
    async def run_loop(self):
        """
        Main rebalancing loop.
        Runs indefinitely until stopped.
        """
        self.running = True
        logger.info(
            "Rebalancer started",
            interval_seconds=self.interval,
            market=settings.market,
            leverage=settings.leverage
        )
        
        while self.running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error("Rebalancer error", error=str(e))
            
            # Wait for next interval
            logger.info(f"Waiting {self.interval} seconds until next check...")
            await asyncio.sleep(self.interval)
        
        logger.info("Rebalancer stopped")
    
    def stop(self):
        """Stop the rebalancing loop."""
        self.running = False
        logger.info("Rebalancer stop requested")
    
    def get_status(self) -> dict:
        """Get the current rebalancer status."""
        return {
            "running": self.running,
            "iteration_count": self.iteration_count,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_action": self.last_action,
            "interval_seconds": self.interval,
            "market": settings.market,
            "leverage": settings.leverage
        }


# Global rebalancer instance
_rebalancer: Optional[Rebalancer] = None


def get_rebalancer() -> Rebalancer:
    """Get or create the global rebalancer instance."""
    global _rebalancer
    if _rebalancer is None:
        _rebalancer = Rebalancer()
    return _rebalancer


async def start_rebalancer():
    """Start the global rebalancer."""
    rebalancer = get_rebalancer()
    await rebalancer.run_loop()


async def test_rebalancer():
    """Test: Run the rebalancer once."""
    rebalancer = Rebalancer()
    result = await rebalancer.run_once()
    print(f"\nRebalancer Result: {result}")
    await rebalancer.strategy.client.close()


if __name__ == "__main__":
    asyncio.run(test_rebalancer())
