"""
FastAPI endpoints for the Funding Rate Vault frontend.
Provides status, position info, and funding history.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
try:
    from .extended_client import ExtendedClient
    from .strategy import UnboundVaultStrategy
    from .rebalancer import get_rebalancer, start_rebalancer
    from .config import settings
    from .starknet_client import vault_monitor, StarknetClient
except ImportError:
    from src.extended_client import ExtendedClient
    from src.strategy import UnboundVaultStrategy
    from src.rebalancer import get_rebalancer, start_rebalancer
    from src.config import settings
    from src.starknet_client import vault_monitor, StarknetClient

app = FastAPI(
    title="Funding Rate Vault API",
    description="Backend API for the BTC Funding Rate Arbitrage Vault",
    version="1.0.0"
)

# CORS for frontend - use settings.frontend_url for production
cors_origins = [settings.frontend_url] if settings.frontend_url else ["http://localhost:3000"]
if settings.frontend_url == "http://localhost:3000":
    cors_origins.append("http://localhost:3001")  # Allow dev ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Authentication ============

async def verify_admin_key(x_api_key: Optional[str] = Header(None)):
    """Verify admin API key for protected endpoints."""
    if not settings.admin_api_key:
        # If no key configured, allow all (for development)
        return True
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


# Global client
_client: Optional[ExtendedClient] = None

# Vault Services
_deposit_processor = None
_withdrawal_processor = None
_position_manager = None
_nav_reporter = None


@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup."""
    import asyncio
    global _deposit_processor, _withdrawal_processor, _position_manager, _nav_reporter
    
    # Import vault queue services
    try:
        from .services.deposit_processor import deposit_processor
        from .services.withdrawal_processor import withdrawal_processor
        from .services.position_manager import position_manager
        from .services.nav_reporter import nav_reporter
        
        _deposit_processor = deposit_processor
        _withdrawal_processor = withdrawal_processor
        _position_manager = position_manager
        _nav_reporter = nav_reporter
        
        # Start vault queue services
        print("🚀 Starting vault queue services...")
        asyncio.create_task(deposit_processor.start())
        asyncio.create_task(withdrawal_processor.start())
        asyncio.create_task(position_manager.start())
        asyncio.create_task(nav_reporter.start())
        print("✅ Vault queue services started")
    except ImportError as e:
        print(f"⚠️ Vault services not available: {e}")
    
    # NOTE: Legacy VaultMonitor disabled - using queue-based system now
    # if not vault_monitor.running:
    #     print("🔍 Starting vault monitor on startup...")
    #     asyncio.create_task(vault_monitor.run_monitor(30))

def get_client() -> ExtendedClient:
    global _client
    if _client is None:
        _client = ExtendedClient()
    return _client


# ============ Response Models ============

class StatusResponse(BaseModel):
    status: str
    funding_rate: float
    funding_rate_percent: str
    estimated_apy: float
    has_position: bool
    position_size: float
    position_value: float
    unrealized_pnl: float
    balance: float
    equity: float
    leverage: float
    market: str
    timestamp: str
    # Delta-neutral fields
    wbtc_held: float = 0.0
    wbtc_value_usd: float = 0.0
    total_nav: float = 0.0
    delta: float = 0.0
    delta_status: str = "UNKNOWN"  # "NEUTRAL", "LONG_HEAVY", "SHORT_HEAVY"


class PositionResponse(BaseModel):
    has_position: bool
    side: Optional[str]
    size: float
    value: float
    open_price: float
    mark_price: float
    liquidation_price: float
    unrealized_pnl: float
    leverage: float


class FundingPaymentResponse(BaseModel):
    market: str
    side: str
    size: float
    funding_fee: float
    funding_rate: float
    paid_time: int
    paid_time_formatted: str


class APYResponse(BaseModel):
    current_funding_rate: float
    hourly_rate_percent: str
    daily_rate_percent: str
    estimated_apy_1x: float
    estimated_apy_2x: float
    estimated_apy_5x: float
    configured_leverage: float
    configured_apy: float
    # Extended exact formula fields
    funding_payment_formula: str
    position_size_btc: float
    mark_price: float
    hourly_funding_payment_usd: float
    daily_funding_payment_usd: float
    annual_funding_payment_usd: float


class RebalancerStatusResponse(BaseModel):
    running: bool
    iteration_count: int
    last_run: Optional[str]
    last_action: Optional[dict]
    interval_seconds: int
    market: str
    leverage: float


# ============ Endpoints ============

@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "Funding Rate Vault API"}


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current vault status including funding rate, position, and delta-neutral metrics."""
    try:
        strategy = UnboundVaultStrategy(get_client())
        state = await strategy.get_state()
        
        # Determine delta status
        if abs(state.delta) < 0.05:
            delta_status = "NEUTRAL"
        elif state.delta > 0:
            delta_status = "LONG_HEAVY"
        else:
            delta_status = "SHORT_HEAVY"
        
        return StatusResponse(
            status="active" if state.has_position else "idle",
            funding_rate=state.funding_rate,
            funding_rate_percent=f"{state.funding_rate * 100:.4f}%",
            estimated_apy=state.estimated_apy,
            has_position=state.has_position,
            position_size=state.position_size,
            position_value=state.position_value,
            unrealized_pnl=state.unrealized_pnl,
            balance=state.balance,
            equity=state.equity,
            leverage=settings.leverage,
            market=settings.market,
            timestamp=datetime.now().isoformat(),
            # Delta-neutral metrics
            wbtc_held=state.wbtc_held,
            wbtc_value_usd=state.wbtc_value_usd,
            total_nav=state.total_nav,
            delta=state.delta,
            delta_status=delta_status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/position", response_model=PositionResponse)
async def get_position():
    """Get current position details."""
    try:
        client = get_client()
        position = await client.get_short_position(settings.market)
        
        if position is None:
            return PositionResponse(
                has_position=False,
                side=None,
                size=0,
                value=0,
                open_price=0,
                mark_price=0,
                liquidation_price=0,
                unrealized_pnl=0,
                leverage=0
            )
        
        return PositionResponse(
            has_position=True,
            side=position.side,
            size=position.size,
            value=position.value,
            open_price=position.open_price,
            mark_price=position.mark_price,
            liquidation_price=position.liquidation_price,
            unrealized_pnl=position.unrealised_pnl,
            leverage=position.leverage
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/funding-history", response_model=List[FundingPaymentResponse])
async def get_funding_history(limit: int = 50):
    """Get funding payment history."""
    try:
        client = get_client()
        payments = await client.get_funding_payments(
            market=settings.market,
            side="SHORT"
        )
        
        result = []
        for payment in payments[:limit]:
            result.append(FundingPaymentResponse(
                market=payment.market,
                side=payment.side,
                size=payment.size,
                funding_fee=payment.funding_fee,
                funding_rate=payment.funding_rate,
                paid_time=payment.paid_time,
                paid_time_formatted=datetime.fromtimestamp(
                    payment.paid_time / 1000
                ).isoformat()
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/apy", response_model=APYResponse)
async def get_apy():
    """
    Get current APY estimates based on funding rate.
    
    Uses Extended's exact formula:
    Funding Payment = Position Size × Mark Price × (-Funding Rate)
    
    If funding rate is positive, shorts receive payment.
    If funding rate is negative, shorts pay.
    """
    try:
        client = get_client()
        funding_rate = await client.get_funding_rate(settings.market)
        mark_price = await client.get_mark_price(settings.market)
        
        # Get current position for actual calculation
        position = await client.get_short_position(settings.market)
        position_size_btc = abs(position.size) if position else 0
        
        # Calculate APY at different leverage levels
        # APY = hourly_rate × 24 hours × 365 days × leverage × 100
        apy_1x = funding_rate * 24 * 365 * 1 * 100
        apy_2x = funding_rate * 24 * 365 * 2 * 100
        apy_5x = funding_rate * 24 * 365 * 5 * 100
        configured_apy = funding_rate * 24 * 365 * settings.leverage * 100
        
        # Extended's exact formula: Position Size × Mark Price × (-Funding Rate)
        # For shorts receiving payment when rate is positive, we use:
        # Funding Payment = position_size × mark_price × funding_rate
        hourly_payment = position_size_btc * mark_price * funding_rate
        daily_payment = hourly_payment * 24
        annual_payment = daily_payment * 365
        
        return APYResponse(
            current_funding_rate=funding_rate,
            hourly_rate_percent=f"{funding_rate * 100:.4f}%",
            daily_rate_percent=f"{funding_rate * 24 * 100:.4f}%",
            estimated_apy_1x=round(apy_1x, 2),
            estimated_apy_2x=round(apy_2x, 2),
            estimated_apy_5x=round(apy_5x, 2),
            configured_leverage=settings.leverage,
            configured_apy=round(configured_apy, 2),
            # Extended exact formula fields
            funding_payment_formula="Position Size × Mark Price × Funding Rate",
            position_size_btc=position_size_btc,
            mark_price=mark_price,
            hourly_funding_payment_usd=round(hourly_payment, 6),
            daily_funding_payment_usd=round(daily_payment, 4),
            annual_funding_payment_usd=round(annual_payment, 2)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rebalancer/status", response_model=RebalancerStatusResponse)
async def get_rebalancer_status():
    """Get rebalancer service status."""
    rebalancer = get_rebalancer()
    status = rebalancer.get_status()
    return RebalancerStatusResponse(**status)


@app.post("/api/rebalancer/start")
async def start_rebalancer_endpoint(background_tasks: BackgroundTasks):
    """Start the rebalancer in the background."""
    rebalancer = get_rebalancer()
    if rebalancer.running:
        return {"status": "already_running"}
    
    background_tasks.add_task(start_rebalancer)
    return {"status": "starting"}


@app.post("/api/rebalancer/stop")
async def stop_rebalancer_endpoint():
    """Stop the rebalancer."""
    rebalancer = get_rebalancer()
    rebalancer.stop()
    return {"status": "stopping"}


@app.post("/api/rebalancer/run-once")
async def run_rebalancer_once():
    """Run the rebalancer once (manual trigger)."""
    try:
        rebalancer = get_rebalancer()
        result = await rebalancer.run_once()
        return {"status": "executed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Wallet Monitor Endpoints ============

class WalletStatusResponse(BaseModel):
    usdc_balance: float
    pending_deposit: float
    operator_wallet: str
    extended_balance: float


@app.get("/api/wallet/status", response_model=WalletStatusResponse)
async def get_wallet_status():
    """Get operator wallet status and pending deposits."""
    try:
        starknet = StarknetClient()
        usdc_balance = await starknet.get_usdc_balance()
        await starknet.close()
        
        # Get Extended balance too
        client = get_client()
        balance = await client.get_balance()
        extended_balance = balance.balance if balance else 0.0
        
        return WalletStatusResponse(
            usdc_balance=usdc_balance,
            pending_deposit=vault_monitor.pending_deposit,
            operator_wallet=settings.operator_address,
            extended_balance=extended_balance
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wallet/check-deposits")
async def check_for_deposits():
    """Manually check for new deposits from vault."""
    try:
        new_amount = await vault_monitor.check_for_new_deposits()
        return {
            "new_deposit": new_amount,
            "pending_total": vault_monitor.pending_deposit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wallet/start-monitor")
async def start_wallet_monitor(background_tasks: BackgroundTasks):
    """Start the wallet monitor in background."""
    if vault_monitor.running:
        return {"status": "already_running"}
    
    background_tasks.add_task(vault_monitor.run_monitor, 30)  # Check every 30s
    return {"status": "starting"}


@app.post("/api/wallet/stop-monitor")
async def stop_wallet_monitor():
    """Stop the wallet monitor."""
    vault_monitor.stop()
    return {"status": "stopped"}


# ============ Legacy Endpoints (Disabled - using queue-based system) ============
# NOTE: These endpoints are deprecated. Deposits are now processed automatically
# by DepositProcessor when it reads the on-chain deposit queue.

# @app.post("/api/wallet/deposit-to-extended")
# async def trigger_deposit_to_extended(amount: float = None, _: bool = Depends(verify_admin_key)):
#     """Manually trigger a deposit to Extended."""
#     ...legacy code...


# ============ Strategy Endpoints ============

# Global strategy instance
_strategy: Optional[UnboundVaultStrategy] = None
_strategy_running = False
_strategy_task = None


def get_strategy() -> UnboundVaultStrategy:
    global _strategy
    if _strategy is None:
        _strategy = UnboundVaultStrategy(get_client())
    return _strategy


@app.get("/api/strategy/status")
async def get_strategy_status():
    """Get current strategy state and market conditions."""
    try:
        strategy = get_strategy()
        state = await strategy.get_state()
        return {
            "status": "running" if _strategy_running else "stopped",
            "funding_rate": state.funding_rate,
            "funding_rate_pct": f"{state.funding_rate * 100:.4f}%",
            "has_position": state.has_position,
            "position_size": state.position_size,
            "position_value": state.position_value,
            "unrealized_pnl": state.unrealized_pnl,
            "balance": state.balance,
            "equity": state.equity,
            "estimated_apy": state.estimated_apy,
            "estimated_apy_pct": f"{state.estimated_apy:.2f}%",
            "market": settings.market,
            "leverage": settings.leverage,
            "open_threshold": settings.funding_threshold_open,
            "close_threshold": settings.funding_threshold_close,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategy/execute")
async def execute_strategy():
    """Manually execute one iteration of the strategy."""
    try:
        strategy = get_strategy()
        result = await strategy.execute_strategy()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategy/open-short")
async def manual_open_short(size_usd: float = 100, _: bool = Depends(verify_admin_key)):
    """Manually open a short position (for testing)."""
    try:
        client = get_client()
        result = await client.open_short_position(settings.market, size_usd)
        return result or {"status": "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategy/close")
async def manual_close_position(_: bool = Depends(verify_admin_key)):
    """Manually close the current position."""
    try:
        client = get_client()
        result = await client.close_position(settings.market)
        return result or {"status": "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_strategy_loop():
    """Background task to run strategy periodically."""
    global _strategy_running
    import asyncio
    
    strategy = get_strategy()
    interval = settings.rebalance_interval_seconds
    
    print(f"🤖 Strategy loop started (interval: {interval}s)")
    
    while _strategy_running:
        try:
            result = await strategy.execute_strategy()
            print(f"Strategy iteration: {result['action']}")
        except Exception as e:
            print(f"Strategy error: {e}")
        
        await asyncio.sleep(interval)
    
    print("🛑 Strategy loop stopped")


@app.post("/api/strategy/start")
async def start_strategy(background_tasks: BackgroundTasks):
    """Start the auto-execution strategy loop."""
    global _strategy_running, _strategy_task
    
    if _strategy_running:
        return {"status": "already_running"}
    
    _strategy_running = True
    background_tasks.add_task(run_strategy_loop)
    return {"status": "started", "interval": settings.rebalance_interval_seconds}


@app.post("/api/strategy/stop")
async def stop_strategy():
    """Stop the auto-execution strategy loop."""
    global _strategy_running
    _strategy_running = False
    return {"status": "stopped"}


# ============ Withdrawal Endpoints ============

@app.post("/api/withdrawal/request")
async def request_withdrawal(amount: float = None, _: bool = Depends(verify_admin_key)):
    """
    Request withdrawal of USDC from Extended to operator wallet.
    
    Args:
        amount: Amount to withdraw in USDC (None = all available)
    """
    try:
        client = get_client()
        result = await client.withdraw_from_extended(amount)
        return result or {"status": "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/withdrawal/prepare-vault")
async def prepare_vault_withdrawal(shares: float, recipient: str = None, _: bool = Depends(verify_admin_key)):
    """
    Prepare for a vault withdrawal:
    1. Calculate USDC value of shares
    2. Close appropriate portion of short position
    3. Withdraw USDC from Extended
    
    Args:
        shares: Number of shares being withdrawn
        recipient: Final recipient of funds (if different from operator)
    """
    try:
        client = get_client()
        result = await client.prepare_vault_withdrawal(shares, recipient)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to prepare withdrawal")
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/withdrawal/status")
async def get_withdrawal_status():
    """Get comprehensive withdrawal status including vault NAV and liquidity."""
    try:
        client = get_client()
        balance = await client.get_balance()
        
        from .starknet_client import StarknetClient
        starknet = StarknetClient()
        operator_balance = await starknet.get_usdc_balance(settings.operator_address)
        
        return {
            "extended_available": balance.available_for_withdrawal if balance else 0,
            "operator_balance": operator_balance,
            "vault_total_usdc": await starknet.get_vault_total_usdc(),
            "vault_total_shares": await starknet.get_vault_total_shares(),
            "has_positions": balance.margin_ratio > 0 if balance else False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/withdrawal/forward-to-vault")
async def forward_usdc_to_vault(amount: float = None, _: bool = Depends(verify_admin_key)):
    """
    Forward USDC from operator wallet to vault contract.
    
    This is called after Extended withdrawal completes.
    The vault needs USDC to swap back to wBTC for user.
    
    Args:
        amount: Amount to forward (None = all available USDC in operator)
    """
    try:
        from src.starknet_client import AutoDepositor, StarknetClient
        
        starknet = StarknetClient()
        depositor = AutoDepositor()
        
        # Get vault address
        vault_address = settings.vault_contract_address
        if not vault_address:
            return {"status": "error", "message": "No vault address configured"}
        
        # Get USDC balance in operator wallet
        if amount is None:
            amount = await starknet.get_usdc_balance()
        
        if amount < 1.0:
            return {"status": "error", "message": f"Insufficient USDC: ${amount:.2f}"}
        
        # Send to vault
        tx_hash = await depositor.send_usdc_to_vault(amount, vault_address)
        
        if tx_hash:
            return {
                "status": "success",
                "amount": amount,
                "tx_hash": tx_hash,
                "vault": vault_address
            }
        else:
            return {"status": "error", "message": "Transfer failed"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Queue Status Endpoints ============

@app.get("/api/queues/status")
async def get_queue_status():
    """Get status of all vault queue services."""
    status = {
        "queue_services_enabled": _deposit_processor is not None,
        "services": {}
    }
    
    if _deposit_processor:
        status["services"]["deposit_processor"] = await _deposit_processor.get_status()
    if _withdrawal_processor:
        status["services"]["withdrawal_processor"] = await _withdrawal_processor.get_status()
    if _position_manager:
        status["services"]["position_manager"] = await _position_manager.get_status()
    if _nav_reporter:
        status["services"]["nav_reporter"] = await _nav_reporter.get_status()
    
    return status


@app.get("/api/queues")
async def get_queues():
    """Get deposit and withdrawal queue status."""
    deposit_status = await _deposit_processor.get_status() if _deposit_processor else None
    withdrawal_status = await _withdrawal_processor.get_status() if _withdrawal_processor else None
    
    return {
        "deposits": deposit_status,
        "withdrawals": withdrawal_status
    }


@app.post("/api/nav/force-update")
async def force_nav_update(_: bool = Depends(verify_admin_key)):
    """Force NAV update (admin only)."""
    if not _nav_reporter:
        raise HTTPException(status_code=503, detail="Queue services not available")
    
    success = await _nav_reporter.force_update()
    return {"success": success}


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global _client, _strategy_running
    
    # Stop queue services
    if _deposit_processor:
        await _deposit_processor.stop()
    if _withdrawal_processor:
        await _withdrawal_processor.stop()
    if _position_manager:
        await _position_manager.stop()
    if _nav_reporter:
        await _nav_reporter.stop()
    
    if _client:
        await _client.close()
    _strategy_running = False
    vault_monitor.stop()

