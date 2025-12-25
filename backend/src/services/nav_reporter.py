"""
NAV Reporter Service for Unbound Vault.

Reports Net Asset Value to the vault contract:
- Calculates NAV from Extended equity
- Applies rate limiting
- Updates vault contract
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..config import settings
from ..extended_client import ExtendedClient
from ..starknet_client import StarknetClient

logger = logging.getLogger(__name__)


class NAVReporter:
    """
    Reports NAV updates to the vault contract.
    
    Flow:
    1. Get equity from Extended
    2. Check if update is allowed (rate limit, cooldown)
    3. Call update_nav() on vault contract
    """
    
    def __init__(self):
        self.starknet = StarknetClient()
        self.extended = ExtendedClient()
        self.running = False
        
        # Update every hour (after Extended funding settlement)
        self.update_interval = 3600  # 1 hour
        self.last_update = None
        self.last_nav = 0
        
        # Rate limit: max 5% change (matching contract constant)
        self.max_change_bps = 500
    
    async def start(self):
        """Start the NAV reporter loop."""
        self.running = True
        logger.info("📈 NAV Reporter started")
        
        while self.running:
            try:
                await self._report_nav()
            except Exception as e:
                logger.error(f"Error in NAV reporter: {e}")
            
            await asyncio.sleep(self.update_interval)
    
    async def stop(self):
        """Stop the NAV reporter."""
        self.running = False
        logger.info("📈 NAV Reporter stopped")
    
    async def _report_nav(self):
        """Calculate and report NAV to vault."""
        # Get current equity from Extended
        equity = await self._get_extended_equity()
        
        if equity <= 0:
            logger.warning("No equity to report")
            return
        
        # Check rate limit
        if not self._is_safe_update(equity):
            logger.warning(f"NAV change too large, skipping update. Current: {self.last_nav}, New: {equity}")
            return
        
        # Update vault
        success = await self._update_vault_nav(equity)
        
        if success:
            self.last_nav = equity
            self.last_update = datetime.now()
            logger.info(f"✅ NAV updated to ${equity:.2f}")
    
    async def _get_extended_equity(self) -> float:
        """Get current equity from Extended."""
        try:
            balance = await self.extended.get_account_balance()
            if balance:
                return balance.equity
            return 0
        except Exception as e:
            logger.error(f"Failed to get Extended equity: {e}")
            return 0
    
    def _is_safe_update(self, new_nav: float) -> bool:
        """Check if NAV update is within rate limits."""
        if self.last_nav <= 0:
            return True  # First update
        
        change_bps = abs(new_nav - self.last_nav) * 10000 / self.last_nav
        return change_bps <= self.max_change_bps
    
    async def _update_vault_nav(self, nav: float) -> bool:
        """Update NAV on the vault contract."""
        try:
            # Convert to 6 decimals (USDC)
            nav_raw = int(nav * 1e6)
            
            result = await self.starknet.invoke_contract(
                settings.vault_contract_address,
                "update_nav",
                [nav_raw]
            )
            
            return result is not None
        except Exception as e:
            logger.error(f"Failed to update vault NAV: {e}")
            return False
    
    async def force_update(self, nav: Optional[float] = None) -> bool:
        """Force NAV update (admin function)."""
        if nav is None:
            nav = await self._get_extended_equity()
        
        if nav <= 0:
            return False
        
        success = await self._update_vault_nav(nav)
        if success:
            self.last_nav = nav
            self.last_update = datetime.now()
        
        return success
    
    async def get_status(self) -> dict:
        """Get reporter status for API."""
        current_equity = await self._get_extended_equity()
        
        return {
            "running": self.running,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_nav": self.last_nav,
            "current_equity": current_equity,
            "update_interval": self.update_interval,
            "next_update_in": self._time_to_next_update()
        }
    
    def _time_to_next_update(self) -> int:
        """Seconds until next scheduled update."""
        if not self.last_update:
            return 0
        
        next_update = self.last_update + timedelta(seconds=self.update_interval)
        remaining = (next_update - datetime.now()).total_seconds()
        return max(0, int(remaining))


# Singleton instance  
nav_reporter = NAVReporter()
