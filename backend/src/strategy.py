"""
Strategy logic for the UnboundVault.
Implements delta-neutral funding rate arbitrage.
"""
from dataclasses import dataclass
from typing import Optional
try:
    from .extended_client import ExtendedClient, Position, Balance
    from .config import settings
except ImportError:
    from src.extended_client import ExtendedClient, Position, Balance
    from src.config import settings
import structlog

logger = structlog.get_logger()


@dataclass
class StrategyState:
    """Current state of the strategy including delta-neutral metrics."""
    funding_rate: float
    has_position: bool
    position_size: float
    position_value: float
    unrealized_pnl: float
    balance: float
    equity: float
    estimated_apy: float
    # Delta-neutral fields
    wbtc_held: float = 0.0          # wBTC in vault (LONG exposure)
    wbtc_value_usd: float = 0.0     # USD value of wBTC
    total_nav: float = 0.0          # wBTC value + Extended equity
    delta: float = 0.0              # Net delta (-1 to +1, target is 0)


class UnboundVaultStrategy:
    """
    Delta-neutral funding rate arbitrage strategy.
    
    The strategy:
    1. Opens a SHORT position when funding rate is positive (longs pay shorts)
    2. Closes position when funding rate turns negative (shorts pay longs)
    3. Collects funding payments every hour
    """
    
    def __init__(self, client: Optional[ExtendedClient] = None):
        self.client = client or ExtendedClient()
        self.market = settings.market
        self.leverage = settings.leverage
        self.open_threshold = settings.funding_threshold_open
        self.close_threshold = settings.funding_threshold_close
    
    async def get_state(self) -> StrategyState:
        """Get the current strategy state including delta-neutral metrics."""
        try:
            from .starknet_client import StarknetClient
            starknet = StarknetClient()
            
            # Get funding rate
            funding_rate = await self.client.get_funding_rate(self.market)
            
            # Get position
            position = await self.client.get_short_position(self.market)
            
            # Get balance
            balance = await self.client.get_balance()
            
            # Get BTC price for delta calculation
            btc_price = await self.client.get_mark_price(self.market)
            
            # Get wBTC held in vault (LONG exposure)
            wbtc_held = await starknet.get_vault_wbtc_held()
            wbtc_value_usd = wbtc_held * btc_price
            
            # Calculate total NAV = wBTC value + Extended equity
            extended_equity = balance.equity if balance else 0
            total_nav = wbtc_value_usd + extended_equity
            
            # Calculate delta: (long_exposure - short_exposure) / total_value
            # Delta = 0 means perfect hedge, >0 means net long, <0 means net short
            long_exposure = wbtc_value_usd
            short_exposure = position.value if position else 0
            delta = (long_exposure - short_exposure) / total_nav if total_nav > 0 else 0
            
            # Calculate estimated APY
            apy = self._calculate_apy(funding_rate)
            
            await starknet.close()
            
            return StrategyState(
                funding_rate=funding_rate,
                has_position=position is not None,
                position_size=position.size if position else 0,
                position_value=position.value if position else 0,
                unrealized_pnl=position.unrealised_pnl if position else 0,
                balance=balance.balance if balance else 0,
                equity=extended_equity,
                estimated_apy=apy,
                wbtc_held=wbtc_held,
                wbtc_value_usd=wbtc_value_usd,
                total_nav=total_nav,
                delta=delta
            )
        except Exception as e:
            logger.error("Failed to get strategy state", error=str(e))
            raise
    
    def _calculate_apy(self, funding_rate: float) -> float:
        """
        Calculate estimated APY from current funding rate.
        Funding rate is hourly, so: APY = rate * 24 * 365 * leverage * 100
        """
        return funding_rate * 24 * 365 * self.leverage * 100
    
    def should_open_position(self, funding_rate: float, has_position: bool) -> bool:
        """
        Determine if we should open a SHORT position.
        
        Open when:
        - No existing position
        - Funding rate is positive (above threshold)
        """
        if has_position:
            return False
        return funding_rate > self.open_threshold
    
    def should_close_position(self, funding_rate: float, has_position: bool) -> bool:
        """
        Determine if we should close the position.
        
        Close when:
        - Have an existing position
        - Funding rate turns negative (below threshold)
        """
        if not has_position:
            return False
        return funding_rate < self.close_threshold
    
    def calculate_position_size(self, available_balance: float) -> float:
        """
        Calculate the position size based on available balance and leverage.
        
        Uses most of available balance with some buffer for safety.
        """
        # Use 90% of available balance to leave room for fees/liquidation
        usable_balance = available_balance * 0.9
        
        # Position size in USD
        return usable_balance * self.leverage
    
    async def execute_strategy(self) -> dict:
        """
        Execute one iteration of the delta-neutral strategy.
        
        Priority order:
        1. Rebalance if delta > 5% threshold
        2. Open SHORT to match wBTC value if no position and funding is positive
        3. Close if funding turns negative
        
        Returns a dict with the action taken and details.
        """
        state = await self.get_state()
        
        logger.info(
            "Strategy check",
            funding_rate=f"{state.funding_rate * 100:.4f}%",
            delta=f"{state.delta:.4f}",
            wbtc_held=f"{state.wbtc_held:.6f}",
            position_value=state.position_value,
            estimated_apy=f"{state.estimated_apy:.2f}%"
        )
        
        # 1. DELTA REBALANCING - if delta exceeds 5% threshold
        DELTA_THRESHOLD = 0.05  # 5%
        if abs(state.delta) > DELTA_THRESHOLD and state.wbtc_value_usd > 0:
            adjustment = state.wbtc_value_usd - state.position_value
            
            if adjustment > 10:  # Need to increase short by more than $10
                logger.info(
                    f"Rebalancing: increasing short by ${adjustment:.2f}",
                    delta=state.delta,
                    wbtc_value=state.wbtc_value_usd,
                    position_value=state.position_value
                )
                result = await self.client.open_short_position(self.market, adjustment)
                return {
                    "action": "REBALANCE_SHORT_UP",
                    "adjustment": adjustment,
                    "delta_before": state.delta,
                    "status": result.get("status") if result else "FAILED",
                    "order": result
                }
            elif adjustment < -10:  # Need to decrease short by more than $10
                btc_price = await self.client.get_mark_price(self.market)
                btc_to_close = abs(adjustment) / btc_price
                logger.info(
                    f"Rebalancing: decreasing short by {btc_to_close:.6f} BTC",
                    delta=state.delta,
                    adjustment=adjustment
                )
                result = await self.client.close_position(self.market, size=btc_to_close)
                return {
                    "action": "REBALANCE_SHORT_DOWN",
                    "adjustment": adjustment,
                    "btc_closed": btc_to_close,
                    "delta_before": state.delta,
                    "status": result.get("status") if result else "FAILED",
                    "order": result
                }
        
        # 2. OPEN POSITION - if no position and funding is positive
        if self.should_open_position(state.funding_rate, state.has_position):
            # For delta-neutral: position size should match wBTC value
            position_size = state.wbtc_value_usd if state.wbtc_value_usd > 0 else self.calculate_position_size(state.equity)
            logger.info(
                "Opening SHORT position to match wBTC value",
                size_usd=position_size,
                wbtc_value=state.wbtc_value_usd,
                funding_rate=state.funding_rate,
                estimated_apy=state.estimated_apy
            )
            
            result = await self.client.open_short_position(self.market, position_size)
            
            return {
                "action": "OPEN_SHORT",
                "size_usd": position_size,
                "funding_rate": state.funding_rate,
                "estimated_apy": state.estimated_apy,
                "status": result.get("status") if result else "FAILED",
                "order": result
            }
        
        # 3. CLOSE POSITION - if funding turns negative
        if self.should_close_position(state.funding_rate, state.has_position):
            logger.info(
                "Closing position due to negative funding",
                position_size=state.position_size,
                unrealized_pnl=state.unrealized_pnl,
                funding_rate=state.funding_rate
            )
            
            result = await self.client.close_position(self.market)
            
            return {
                "action": "CLOSE_POSITION",
                "position_size": state.position_size,
                "unrealized_pnl": state.unrealized_pnl,
                "funding_rate": state.funding_rate,
                "status": result.get("status") if result else "FAILED",
                "order": result
            }
        
        # No action needed - delta is within range and funding is acceptable
        return {
            "action": "HOLD",
            "funding_rate": state.funding_rate,
            "has_position": state.has_position,
            "delta": state.delta,
            "wbtc_value_usd": state.wbtc_value_usd,
            "position_value": state.position_value,
            "estimated_apy": state.estimated_apy
        }
    
    def calculate_nav(self, balance: float, unrealized_pnl: float) -> float:
        """
        Calculate Net Asset Value.
        NAV = balance + unrealized PnL
        """
        return balance + unrealized_pnl


async def test_strategy():
    """Test the strategy logic."""
    strategy = UnboundVaultStrategy()
    
    print("=" * 60)
    print("Testing Strategy Logic")
    print("=" * 60)
    
    try:
        state = await strategy.get_state()
        print(f"\nCurrent State:")
        print(f"  Funding Rate: {state.funding_rate * 100:.4f}%")
        print(f"  Has Position: {state.has_position}")
        print(f"  Position Size: ${state.position_size:,.2f}")
        print(f"  Balance: ${state.balance:,.2f}")
        print(f"  Equity: ${state.equity:,.2f}")
        print(f"  Estimated APY: {state.estimated_apy:.2f}%")
        
        print(f"\nStrategy Decision:")
        result = await strategy.execute_strategy()
        print(f"  Action: {result['action']}")
        for k, v in result.items():
            if k != 'action':
                print(f"  {k}: {v}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await strategy.client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_strategy())
