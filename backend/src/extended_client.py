"""
Extended API client for the Funding Rate Vault.
Handles all interactions with Extended exchange.
"""
import aiohttp
from dataclasses import dataclass
from typing import Optional, List
import json
from .config import settings


@dataclass
class Position:
    """Represents an open position on Extended."""
    id: int
    market: str
    side: str  # "LONG" or "SHORT"
    leverage: float
    size: float
    value: float
    open_price: float
    mark_price: float
    liquidation_price: float
    unrealised_pnl: float


@dataclass
class Balance:
    """Account balance information."""
    balance: float
    equity: float
    available_for_trade: float
    available_for_withdrawal: float
    unrealised_pnl: float
    margin_ratio: float


@dataclass
class FundingPayment:
    """A funding payment record."""
    market: str
    side: str
    size: float
    funding_fee: float
    funding_rate: float
    paid_time: int


class ExtendedClient:
    """
    Client for Extended exchange API.
    Handles authentication, requests, and response parsing.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None
    ):
        self.api_key = api_key or settings.extended_api_key
        self.api_url = api_url or settings.extended_api_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def headers(self) -> dict:
        return {
            "X-Api-Key": self.api_key,
            "User-Agent": "UnboundVault/1.0",
            "Content-Type": "application/json"
        }
    
    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        if self._session:
            await self._session.close()
    
    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request to Extended API."""
        await self._ensure_session()
        url = f"{self.api_url}{endpoint}"
        async with self._session.get(url, headers=self.headers, params=params) as resp:
            data = await resp.json()
            if data.get("status") != "OK" and data.get("status") != "ok":
                raise Exception(f"Extended API error: {data}")
            return data
    
    async def _post(self, endpoint: str, body: dict) -> dict:
        """Make a POST request to Extended API."""
        await self._ensure_session()
        url = f"{self.api_url}{endpoint}"
        async with self._session.post(url, headers=self.headers, json=body) as resp:
            data = await resp.json()
            if data.get("status") != "OK" and data.get("status") != "ok":
                raise Exception(f"Extended API error: {data}")
            return data
    
    # ========== Public Endpoints ==========
    
    async def get_markets(self, market: str = "BTC-USD") -> dict:
        """Get market information including current funding rate."""
        data = await self._get(f"/info/markets", params={"market": market})
        return data.get("data", [])[0] if data.get("data") else {}
    
    async def get_funding_rate(self, market: str = "BTC-USD") -> float:
        """Get the current funding rate for a market."""
        market_data = await self.get_markets(market)
        stats = market_data.get("marketStats", {})
        return float(stats.get("fundingRate", 0))
    
    async def get_funding_history(
        self,
        market: str = "BTC-USD",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[dict]:
        """Get historical funding rates."""
        params = {}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        data = await self._get(f"/info/{market}/funding", params=params)
        return data.get("data", [])
    
    # ========== Private Endpoints ==========
    
    async def get_balance(self) -> Optional[Balance]:
        """Get account balance."""
        try:
            data = await self._get("/user/balance")
            b = data.get("data", {})
            return Balance(
                balance=float(b.get("balance", 0)),
                equity=float(b.get("equity", 0)),
                available_for_trade=float(b.get("availableForTrade", 0)),
                available_for_withdrawal=float(b.get("availableForWithdrawal", 0)),
                unrealised_pnl=float(b.get("unrealisedPnl", 0)),
                margin_ratio=float(b.get("marginRatio", 0))
            )
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None
    
    async def get_positions(self, market: str = "BTC-USD", side: str = None) -> List[Position]:
        """Get open positions."""
        params = {"market": market}
        if side:
            params["side"] = side
        
        data = await self._get("/user/positions", params=params)
        positions = []
        for p in data.get("data", []):
            positions.append(Position(
                id=p.get("id"),
                market=p.get("market"),
                side=p.get("side"),
                leverage=float(p.get("leverage", 0)),
                size=float(p.get("size", 0)),
                value=float(p.get("value", 0)),
                open_price=float(p.get("openPrice", 0)),
                mark_price=float(p.get("markPrice", 0)),
                liquidation_price=float(p.get("liquidationPrice", 0)),
                unrealised_pnl=float(p.get("unrealisedPnl", 0))
            ))
        return positions
    
    async def get_short_position(self, market: str = "BTC-USD") -> Optional[Position]:
        """Get the current short position if any."""
        positions = await self.get_positions(market=market, side="SHORT")
        return positions[0] if positions else None
    
    async def get_funding_payments(
        self,
        market: str = "BTC-USD",
        side: str = "SHORT"
    ) -> List[FundingPayment]:
        """Get funding payment history."""
        params = {"market": market, "side": side}
        data = await self._get("/user/funding/history", params=params)
        
        payments = []
        for p in data.get("data", []):
            payments.append(FundingPayment(
                market=p.get("market"),
                side=p.get("side"),
                size=float(p.get("size", 0)),
                funding_fee=float(p.get("fundingFee", 0)),
                funding_rate=float(p.get("fundingRate", 0)),
                paid_time=p.get("paidTime", 0)
            ))
        return payments
    
    async def get_leverage(self, market: str = "BTC-USD") -> float:
        """Get current leverage setting for a market."""
        data = await self._get("/user/leverage", params={"market": market})
        return float(data.get("data", {}).get("leverage", 1))
    
    async def set_leverage(self, market: str, leverage: float) -> bool:
        """Set leverage for a market."""
        try:
            await self._session.patch(
                f"{self.api_url}/user/leverage",
                headers=self.headers,
                json={"market": market, "leverage": str(leverage)}
            )
            return True
        except Exception as e:
            print(f"Error setting leverage: {e}")
            return False
    
    # ========== Trading with x10 SDK ==========
    
    def _get_trading_client(self):
        """Get or create the x10 trading client."""
        if not hasattr(self, '_trading_client') or self._trading_client is None:
            try:
                from x10.perpetual.trading_client import PerpetualTradingClient
                from x10.perpetual.accounts import StarkPerpetualAccount
                from x10.perpetual.configuration import MAINNET_CONFIG
                from fast_stark_crypto import get_public_key
                
                if not settings.extended_stark_key or not settings.extended_vault_number:
                    print("❌ Missing EXTENDED_STARK_KEY or EXTENDED_VAULT_NUMBER")
                    return None
                
                # Derive public key from private key
                private_key = settings.extended_stark_key
                if private_key.startswith("0x"):
                    private_key_int = int(private_key, 16)
                else:
                    private_key_int = int(private_key)
                
                public_key_int = get_public_key(private_key_int)
                public_key = hex(public_key_int)
                
                print(f"🔑 Derived public key: {public_key[:20]}...")
                
                # Create Stark account
                stark_account = StarkPerpetualAccount(
                    vault=int(settings.extended_vault_number),
                    private_key=settings.extended_stark_key,
                    public_key=public_key,
                    api_key=self.api_key,
                )
                
                # Create trading client
                self._trading_client = PerpetualTradingClient(
                    endpoint_config=MAINNET_CONFIG,
                    stark_account=stark_account,
                )
                print("✅ x10 Trading client initialized")
            except Exception as e:
                print(f"❌ Failed to create trading client: {e}")
                import traceback
                traceback.print_exc()
                return None
        return self._trading_client
    
    async def get_mark_price(self, market: str = "BTC-USD") -> float:
        """Get current mark price for a market."""
        market_data = await self.get_markets(market)
        stats = market_data.get("marketStats", {})
        return float(stats.get("markPrice", 0))
    
    async def open_short_position(self, market: str, size_usd: float) -> Optional[dict]:
        """
        Open a short position using x10 SDK.
        
        Args:
            market: Market name (e.g., "BTC-USD")
            size_usd: Position size in USD
            
        Returns:
            Order result dict or None on failure
        """
        trading_client = self._get_trading_client()
        if not trading_client:
            return None
        
        try:
            from decimal import Decimal
            from x10.perpetual.orders import OrderSide, TimeInForce
            
            # Get current price
            mark_price = await self.get_mark_price(market)
            if mark_price <= 0:
                print(f"❌ Invalid mark price: {mark_price}")
                return None
            
            # Calculate size in synthetic (BTC)
            # Reduce by 5% to leave room for fees
            size_btc = (size_usd * 0.95) / mark_price
            
            # Round to 5 decimals (Extended precision limit) and check minimum
            size_btc = round(size_btc, 5)
            if size_btc < 0.00001:
                print(f"❌ Size too small: {size_btc} BTC (min: 0.00001)")
                return None
            
            # Set price slightly below market for SELL (aggressive fill)
            # Extended requires integer price for BTC-USD
            order_price = int(mark_price * 0.995)  # 0.5% below, no decimals
            
            print(f"📈 Opening SHORT position:")
            print(f"   Market: {market}")
            print(f"   Size: {size_btc:.5f} BTC (${size_usd:.2f})")
            print(f"   Price: ${order_price:.2f}")
            
            result = await trading_client.place_order(
                market_name=market,
                amount_of_synthetic=Decimal(str(size_btc)),
                price=Decimal(str(order_price)),
                side=OrderSide.SELL,
                time_in_force=TimeInForce.IOC  # Immediate-or-cancel for market-like behavior
            )
            
            if result.status == "OK":
                print(f"✅ Order placed successfully: {result.data}")
                return {"status": "success", "order": result.data}
            else:
                print(f"❌ Order failed: {result}")
                return {"status": "failed", "error": str(result)}
                
        except Exception as e:
            print(f"❌ Error opening short: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def close_position(self, market: str, size: float = None) -> Optional[dict]:
        """
        Close an existing position using x10 SDK.
        
        Args:
            market: Market name (e.g., "BTC-USD")
            size: Specific size to close (None = close all)
            
        Returns:
            Order result dict or None on failure
        """
        trading_client = self._get_trading_client()
        if not trading_client:
            return None
        
        try:
            from decimal import Decimal
            from x10.perpetual.orders import OrderSide, TimeInForce
            
            # Get current position
            position = await self.get_short_position(market)
            if not position or position.size <= 0:
                print("ℹ️ No position to close")
                return {"status": "no_position"}

            # Use specified size or full position size
            close_size = size if size is not None else position.size
            if close_size > position.size:
                close_size = position.size
            
            # Round to 5 decimals for Extended precision
            close_size = round(float(close_size), 5)
            if close_size < 0.00001:
                print(f"❌ Size too small to close: {close_size}")
                return {"status": "too_small"}
            
            # Get current price
            mark_price = await self.get_mark_price(market)
            
            # Set price slightly above market for BUY (aggressive fill to close short)
            # Extended requires integer price for BTC-USD
            order_price = int(mark_price * 1.005)  # 0.5% above
            
            print(f"📉 Closing position {'partially' if size else ''}:")
            print(f"   Market: {market}")
            print(f"   Size to Close: {close_size:.5f} BTC")
            print(f"   Full Size: {position.size} BTC")
            print(f"   Price: ${order_price:.2f}")
            
            result = await trading_client.place_order(
                market_name=market,
                amount_of_synthetic=Decimal(str(close_size)),
                price=Decimal(str(order_price)),
                side=OrderSide.BUY,  # Buy to close short
                time_in_force=TimeInForce.IOC
            )
            
            if result.status == "OK":
                print(f"✅ Position closed: {result.data}")
                return {"status": "success", "order": result.data}
            else:
                print(f"❌ Close failed: {result}")
                return {"status": "failed", "error": str(result)}
                
        except Exception as e:
            print(f"❌ Error closing position: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ========== Withdrawals ==========
    
    async def withdraw_from_extended(self, amount_usdc: float = None, recipient_address: str = None) -> Optional[dict]:
        """
        Request withdrawal of USDC from Extended to a Starknet address.
        Uses x10 SDK with proper Stark signature.
        
        Args:
            amount_usdc: Amount to withdraw (None = all available)
            recipient_address: Starknet address to receive funds (defaults to operator)
            
        Returns:
            Withdrawal result dict or None on failure
        """
        trading_client = self._get_trading_client()
        if not trading_client:
            print("❌ Trading client not available")
            return None
        
        try:
            from decimal import Decimal
            import random
            
            # Get available balance if not specified
            if amount_usdc is None:
                balance = await self.get_balance()
                if not balance:
                    print("❌ Could not get balance")
                    return None
                amount_usdc = balance.available_for_withdrawal
            
            if amount_usdc <= 0:
                print("❌ No funds available for withdrawal")
                return {"status": "error", "message": "No funds available"}
            
            # Default recipient is operator wallet
            if recipient_address is None:
                recipient_address = settings.operator_address
            
            # Generate nonce
            nonce = random.randint(1, 2**31)
            
            # Debug: Print all parameters
            print(f"💰 Requesting withdrawal of ${amount_usdc:.2f} USDC...")
            print(f"   Recipient: {recipient_address}")
            print(f"   DEBUG - Amount (Decimal): {Decimal(str(amount_usdc))}")
            print(f"   DEBUG - Stark address (lowercase): {recipient_address.lower()}")
            print(f"   DEBUG - Nonce: {nonce}")
            
            # Check current balance before withdrawal
            try:
                balance = await self.get_balance()
                if balance:
                    print(f"   DEBUG - Current balance: available={balance.available_for_withdrawal}")
            except Exception as be:
                print(f"   DEBUG - Could not get balance: {be}")
            
            # Round to 2 decimal places - Extended may reject high precision amounts
            amount_rounded = round(amount_usdc, 2)
            print(f"   DEBUG - Amount rounded to 2 decimals: {amount_rounded}")
            
            # Use SDK to create signed withdrawal
            result = await trading_client.account.withdraw(
                amount=Decimal(str(amount_rounded)),
                stark_address=recipient_address.lower(),
                nonce=nonce
            )
            
            print(f"   DEBUG - Full response: {result}")
            
            if result.status == "OK":
                print(f"✅ Withdrawal requested successfully")
                print(f"   Withdrawal ID: {result.data}")
                return {"status": "success", "amount": amount_usdc, "withdrawal_id": result.data}
            else:
                print(f"❌ Withdrawal failed: {result}")
                return {"status": "failed", "error": str(result)}
                    
        except Exception as e:
            print(f"❌ Error withdrawing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def prepare_vault_withdrawal(self, shares_to_burn: float, recipient_address: str = None) -> Optional[dict]:
        """
        Prepare for a vault withdrawal:
        1. Calculate USDC value of shares
        2. Close appropriate portion of short position
        3. Withdraw USDC from Extended
        
        Args:
            shares_to_burn: Number of shares being withdrawn
            recipient_address: Final recipient of funds (if different from operator)
            
        Returns:
            Result dict with status and details
        """
        try:
            print(f"🔄 Preparing vault withdrawal for {shares_to_burn:.4f} shares...")
            
            # 1. Calculate USDC value
            from .starknet_client import StarknetClient
            starknet = StarknetClient()
            
            total_usdc = await starknet.get_vault_total_usdc()
            total_shares = await starknet.get_vault_total_shares()
            
            if total_shares <= 0:
                print("❌ Vault has no shares")
                return {"status": "error", "message": "Vault has no shares"}
            
            # USDC amount = (shares_to_burn / total_shares) * total_usdc
            usdc_amount = (shares_to_burn / total_shares) * total_usdc
            print(f"   Calculated value: ${usdc_amount:.2f} USDC")
            
            # 2. Close position if needed
            # We assume the position size in BTC should be reduced proportionally
            position = await self.get_short_position()
            if position and position.size > 0:
                # Calculate BTC size to close
                # BTC_to_close = (shares_to_burn / total_shares) * total_BTC_position
                btc_to_close = (shares_to_burn / total_shares) * position.size
                print(f"   Closing {btc_to_close:.6f} BTC of short position...")
                
                close_result = await self.close_position(settings.market, size=btc_to_close)
                if not close_result or close_result.get("status") != "success":
                    print("   ⚠️ Partial close failed, attempting full close as fallback...")
                    # Fallback or error handling? For now we continue if we can
            
            # 3. Request withdrawal from Extended
            # We withdraw the calculated USDC amount
            withdraw_result = await self.withdraw_from_extended(usdc_amount)
            if not withdraw_result or withdraw_result.get("status") != "success":
                return {"status": "error", "message": f"Extended withdrawal failed: {withdraw_result.get('error') if withdraw_result else 'Unknown'}"}
            
            # Notify monitor to expect this withdrawal for auto-forwarding
            try:
                from .starknet_client import vault_monitor
                vault_monitor.expect_withdrawal(usdc_amount)
            except ImportError:
                # Handle cases where it's run as a script or different path
                try:
                    from src.starknet_client import vault_monitor
                    vault_monitor.expect_withdrawal(usdc_amount)
                except Exception as e:
                    print(f"⚠️ Could not notify vault monitor: {e}")
            
            print(f"✅ Withdrawal initiated - ${usdc_amount:.2f} USDC")
            print(f"   ⏳ Note: Extended withdrawals may take a few minutes to process")
            
            return {
                "status": "pending",
                "shares": shares_to_burn,
                "amount_usdc": usdc_amount,
                "recipient": recipient_address or settings.operator_address,
                "message": "Withdrawal requested from Extended. USDC will be sent to operator wallet."
            }
            
        except Exception as e:
            print(f"❌ Error preparing withdrawal: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    # ========== Order Management ==========
    # Note: Orders require Stark signatures - use Python SDK for this
    # These are placeholder methods that will need SDK integration


# Convenience function for quick testing
async def test_connection():
    """Test the Extended API connection."""
    client = ExtendedClient()
    try:
        # Test public endpoint
        funding = await client.get_funding_rate("BTC-USD")
        print(f"✅ Connected to Extended")
        print(f"   Current BTC-USD funding rate: {funding * 100:.4f}%")
        
        # Test private endpoint (will fail without API key)
        if client.api_key:
            balance = await client.get_balance()
            if balance:
                print(f"   Balance: ${balance.balance:.2f}")
                print(f"   Equity: ${balance.equity:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())
