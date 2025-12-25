"""
Position Manager Service for Unbound Vault.

Manages the delta-neutral strategy:
- Monitors position health (margin ratio, liquidation risk)
- Rebalances position based on NAV changes
- Handles negative funding rate scenarios
- Compounds funding rate earnings
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..config import settings
from ..extended_client import ExtendedClient

logger = logging.getLogger(__name__)


@dataclass
class PositionHealth:
    """Position health metrics."""
    size: float
    entry_price: float
    mark_price: float
    margin_ratio: float
    unrealized_pnl: float
    funding_rate: float
    is_healthy: bool


class PositionManager:
    """
    Manages the short BTC-PERP position on Extended.
    
    Responsibilities:
    - Monitor position health
    - Rebalance when NAV changes significantly
    - Close position if funding rate goes negative
    - Compound earnings periodically
    """
    
    def __init__(self):
        self.extended = ExtendedClient()
        self.running = False
        self.check_interval = 60  # Check every minute
        self.rebalance_threshold = 0.05  # 5% drift triggers rebalance
        self.negative_funding_threshold = -0.0001  # -0.01% closes position
        
        # State
        self.last_rebalance = None
        self.position_closed_due_to_funding = False
    
    async def start(self):
        """Start the position manager loop."""
        self.running = True
        logger.info("📊 Position Manager started")
        
        while self.running:
            try:
                await self._check_position_health()
                await self._check_funding_rate()
            except Exception as e:
                logger.error(f"Error in position manager: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the position manager."""
        self.running = False
        logger.info("📊 Position Manager stopped")
    
    async def _check_position_health(self):
        """Check and log position health metrics."""
        health = await self.get_position_health()
        
        if not health:
            logger.debug("No active position")
            return
        
        if health.margin_ratio > 0.8:
            logger.warning(f"⚠️ HIGH MARGIN RATIO: {health.margin_ratio:.1%}")
            # Could trigger automatic deleveraging here
        
        if not health.is_healthy:
            logger.error("🚨 POSITION UNHEALTHY - Consider intervention")
    
    async def _check_funding_rate(self):
        """Check funding rate and close position if negative."""
        try:
            funding_rate = await self.extended.get_funding_rate(settings.market)
            
            if funding_rate < self.negative_funding_threshold:
                if not self.position_closed_due_to_funding:
                    logger.warning(f"📉 Negative funding rate: {funding_rate:.4%} - Closing position")
                    await self._close_all_positions()
                    self.position_closed_due_to_funding = True
            else:
                # Reopen if funding went positive again
                if self.position_closed_due_to_funding:
                    logger.info(f"📈 Funding rate positive: {funding_rate:.4%} - Can reopen position")
                    self.position_closed_due_to_funding = False
                    
        except Exception as e:
            logger.error(f"Error checking funding rate: {e}")
    
    async def _close_all_positions(self):
        """Close all positions to avoid paying negative funding."""
        try:
            await self.extended.close_position(settings.market)
            logger.info("✅ All positions closed")
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    async def rebalance_to_nav(self, target_nav: float):
        """
        Rebalance position to match target NAV.
        Called after deposits/withdrawals are processed.
        """
        try:
            current_position = await self._get_current_position_value()
            target_position = target_nav * settings.leverage
            
            diff = target_position - current_position
            
            if abs(diff / target_position) < self.rebalance_threshold:
                logger.debug("Position within threshold, no rebalance needed")
                return
            
            if diff > 0:
                # Need to increase short
                logger.info(f"📈 Increasing position by ${diff:.2f}")
                await self.extended.open_short_position(settings.market, diff)
            else:
                # Need to decrease short
                logger.info(f"📉 Decreasing position by ${-diff:.2f}")
                await self.extended.close_position(settings.market, size=-diff)
            
            self.last_rebalance = datetime.now()
            logger.info("✅ Position rebalanced")
            
        except Exception as e:
            logger.error(f"Error rebalancing position: {e}")
    
    async def _get_current_position_value(self) -> float:
        """Get current position value in USD."""
        try:
            positions = await self.extended.get_positions()
            if not positions:
                return 0
            
            btc_pos = next((p for p in positions if p.market == settings.market), None)
            return abs(btc_pos.size * btc_pos.mark_price) if btc_pos else 0
        except Exception as e:
            logger.error(f"Error getting position value: {e}")
            return 0
    
    async def get_position_health(self) -> Optional[PositionHealth]:
        """Get current position health metrics."""
        try:
            positions = await self.extended.get_positions()
            if not positions:
                return None
            
            btc_pos = next((p for p in positions if p.market == settings.market), None)
            if not btc_pos:
                return None
            
            funding_rate = await self.extended.get_funding_rate(settings.market)
            
            return PositionHealth(
                size=btc_pos.size,
                entry_price=btc_pos.entry_price,
                mark_price=btc_pos.mark_price,
                margin_ratio=btc_pos.margin_ratio if hasattr(btc_pos, 'margin_ratio') else 0,
                unrealized_pnl=btc_pos.unrealized_pnl if hasattr(btc_pos, 'unrealized_pnl') else 0,
                funding_rate=funding_rate,
                is_healthy=btc_pos.margin_ratio < 0.7 if hasattr(btc_pos, 'margin_ratio') else True
            )
        except Exception as e:
            logger.error(f"Error getting position health: {e}")
            return None
    
    async def get_status(self) -> dict:
        """Get manager status for API."""
        health = await self.get_position_health()
        return {
            "running": self.running,
            "position_closed_due_to_funding": self.position_closed_due_to_funding,
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
            "position": {
                "size": health.size,
                "entry_price": health.entry_price,
                "mark_price": health.mark_price,
                "margin_ratio": health.margin_ratio,
                "unrealized_pnl": health.unrealized_pnl,
                "funding_rate": health.funding_rate,
                "is_healthy": health.is_healthy
            } if health else None
        }


# Singleton instance
position_manager = PositionManager()
