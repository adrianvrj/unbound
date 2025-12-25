"""
Withdrawal Processor Service for Unbound Vault.

Handles the withdrawal queue state machine:
PENDING -> PROCESSING -> READY -> COMPLETED

Workflow:
1. Monitor on-chain withdrawal requests
2. Close proportional position on Extended
3. Request USDC withdrawal from Extended
4. Monitor for USDC arrival in operator wallet
5. Forward USDC to vault
6. Call mark_withdrawal_ready() on vault
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
from enum import IntEnum

from ..config import settings
from ..extended_client import ExtendedClient
from ..starknet_client import StarknetClient

logger = logging.getLogger(__name__)


class WithdrawalStatus(IntEnum):
    """Withdrawal status matching on-chain enum."""
    PENDING = 0
    PROCESSING = 1
    READY = 2
    COMPLETED = 3
    CANCELLED = 4


@dataclass
class WithdrawalQueueItem:
    """Represents a pending withdrawal from the on-chain queue."""
    request_id: int
    user: str
    shares: int
    min_assets: int
    usdc_value: float
    timestamp: int
    status: WithdrawalStatus


class WithdrawalProcessor:
    """
    Processes withdrawals from the V2 vault queue.
    
    State machine:
    - PENDING: User requested, shares locked
    - PROCESSING: Backend closing position, waiting for Extended withdrawal
    - READY: USDC forwarded to vault, user can complete
    - COMPLETED: User received wBTC
    - CANCELLED: User cancelled (shares returned)
    """
    
    def __init__(self):
        self.starknet = StarknetClient()
        self.extended = ExtendedClient()
        self.running = False
        self.processing_interval = 30  # seconds
        
        # Track withdrawals in processing
        self.processing_withdrawals: Dict[int, dict] = {}
    
    async def start(self):
        """Start the withdrawal processor loop."""
        self.running = True
        logger.info("📤 Withdrawal Processor started")
        
        while self.running:
            try:
                print("📤 WithdrawalProcessor: checking for pending withdrawals...")
                await self._process_pending_withdrawals()
                await self._check_processing_withdrawals()
                print("📤 WithdrawalProcessor: check complete, sleeping 30s")
            except Exception as e:
                print(f"❌ Error in withdrawal processor: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(self.processing_interval)
    
    async def stop(self):
        """Stop the withdrawal processor."""
        self.running = False
        logger.info("📤 Withdrawal Processor stopped")
    
    async def _process_pending_withdrawals(self):
        """Find and start processing PENDING withdrawals."""
        queue_length = await self._get_withdrawal_queue_length()
        
        print(f"📤 Withdrawal queue check: {queue_length} total items")
        
        if queue_length == 0:
            return
        
        # Scan for pending withdrawals
        for request_id in range(queue_length):
            withdrawal = await self._get_pending_withdrawal(request_id)
            
            if withdrawal:
                print(f"   Withdrawal #{request_id}: status={withdrawal.status.name}")
            else:
                print(f"   Withdrawal #{request_id}: ERROR - could not fetch")
            
            if withdrawal and withdrawal.status == WithdrawalStatus.PENDING:
                print(f"   → Status is PENDING, checking if already processing...")
                if request_id not in self.processing_withdrawals:
                    print(f"   → Not in processing list, starting processing...")
                    await self._start_processing(withdrawal)
                else:
                    print(f"   → Already being processed, skipping")
    
    async def _start_processing(self, withdrawal: WithdrawalQueueItem):
        """Start processing a pending withdrawal."""
        logger.info(f"🔄 Starting to process withdrawal #{withdrawal.request_id}")
        
        try:
            # Calculate USDC value for shares (this is TOTAL value based on NAV)
            usdc_value = await self._calculate_usdc_value(withdrawal.shares)
            
            if usdc_value <= 0:
                logger.error(f"Invalid USDC value for withdrawal #{withdrawal.request_id}")
                return
            
            # Only half of the value is in Extended (USDC)
            # The other half is wBTC held in vault
            extended_usdc = usdc_value / 2
            
            # Track this withdrawal
            self.processing_withdrawals[withdrawal.request_id] = {
                "user": withdrawal.user,
                "shares": withdrawal.shares,
                "usdc_value": extended_usdc,  # Store the Extended USDC portion
                "started_at": datetime.now(),
                "step": "closing_position"
            }
            
            # Step 1: Close proportional position
            position_closed = await self._close_proportional_position(extended_usdc)
            if not position_closed:
                logger.warning(f"Could not close position for withdrawal #{withdrawal.request_id}")
                # Continue anyway, may have already been closed
            
            # Step 2: Request withdrawal from Extended (only the USDC portion)
            withdrawal_requested = await self.extended.withdraw_from_extended(extended_usdc)
            if withdrawal_requested:
                self.processing_withdrawals[withdrawal.request_id]["step"] = "waiting_usdc"
                logger.info(f"✅ Extended withdrawal requested for ${extended_usdc:.2f}")
            else:
                logger.error(f"Failed to request Extended withdrawal")
                # Remove from processing so it can retry on next cycle
                del self.processing_withdrawals[withdrawal.request_id]
                
        except Exception as e:
            logger.error(f"Error starting withdrawal #{withdrawal.request_id}: {e}")
            # Clean up failed processing attempt so it can retry
            if withdrawal.request_id in self.processing_withdrawals:
                del self.processing_withdrawals[withdrawal.request_id]
    
    async def _check_processing_withdrawals(self):
        """Check status of withdrawals being processed."""
        completed = []
        
        for request_id, data in self.processing_withdrawals.items():
            if data["step"] == "waiting_usdc":
                # Check if USDC arrived in operator wallet
                usdc_balance = await self.starknet.get_usdc_balance()
                
                if usdc_balance >= data["usdc_value"]:
                    # Forward USDC to vault and mark ready
                    success = await self._complete_processing(request_id, data)
                    if success:
                        completed.append(request_id)
        
        # Clean up completed
        for request_id in completed:
            del self.processing_withdrawals[request_id]
    
    async def _complete_processing(self, request_id: int, data: dict) -> bool:
        """Complete withdrawal processing by marking it ready."""
        logger.info(f"✅ USDC arrived for withdrawal #{request_id}")
        
        try:
            # Forward USDC to vault contract using AutoDepositor
            from ..starknet_client import AutoDepositor
            depositor = AutoDepositor()
            forward_success = await depositor.send_usdc_to_vault(data["usdc_value"], settings.vault_contract_address)
            if not forward_success:
                logger.error(f"Failed to forward USDC to vault")
                return False
            
            # Call mark_withdrawal_ready on vault
            # Args: request_id, usdc_amount (in 6 decimals)
            usdc_amount_raw = int(data["usdc_value"] * 1e6)
            
            result = await self.starknet.invoke_contract(
                settings.vault_contract_address,
                "mark_withdrawal_ready",
                [request_id, usdc_amount_raw],
                u256_indices=[0, 1]  # Both params are u256
            )
            
            if result:
                logger.info(f"✅ Withdrawal #{request_id} marked as READY (${data['usdc_value']:.2f})")
                return True
            else:
                logger.error(f"Failed to mark withdrawal ready")
                return False
                
        except Exception as e:
            logger.error(f"Error completing withdrawal #{request_id}: {e}")
            return False
    
    async def _calculate_usdc_value(self, shares: int) -> float:
        """Calculate USDC value for given shares."""
        try:
            # Call vault.preview_redeem(shares)
            result = await self.starknet.call_contract(
                settings.vault_contract_address,
                "preview_redeem",
                [shares],
                u256_indices=[0]  # shares is u256
            )
            return float(result[0]) / 1e6 if result else 0
        except Exception as e:
            logger.error(f"Failed to calculate USDC value: {e}")
            return 0
    
    async def _close_proportional_position(self, usdc_amount: float) -> bool:
        """Close proportional short position for withdrawal."""
        try:
            # Get current position size
            positions = await self.extended.get_positions()
            if not positions:
                return True  # No position to close
            
            btc_position = next((p for p in positions if p.market == settings.market), None)
            if not btc_position:
                return True
            
            # Calculate proportional close
            close_size = usdc_amount * settings.leverage
            
            if abs(btc_position.size) > close_size:
                # Partial close
                await self.extended.close_position(settings.market, size=close_size)
            else:
                # Full close
                await self.extended.close_position(settings.market)
            
            return True
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    async def _get_withdrawal_queue_length(self) -> int:
        """Get the number of pending withdrawals from the vault."""
        try:
            result = await self.starknet.call_contract(
                settings.vault_contract_address,
                "get_withdrawal_queue_length",
                []
            )
            return int(result[0]) if result else 0
        except Exception as e:
            logger.error(f"Failed to get withdrawal queue length: {e}")
            return 0
    
    async def _get_pending_withdrawal(self, request_id: int) -> Optional[WithdrawalQueueItem]:
        """Get a specific pending withdrawal from the vault."""
        try:
            result = await self.starknet.call_contract(
                settings.vault_contract_address,
                "get_pending_withdrawal",
                [request_id],
                u256_indices=[0]  # request_id is u256
            )
            
            if not result:
                return None
            
            # Debug: print raw result
            print(f"   DEBUG get_pending_withdrawal raw result: {result}")
            
            # Parse the withdrawal request struct
            # RPC returns u256 as two felts (low, high), so struct layout is:
            # [0]=user, [1,2]=shares, [3,4]=min_assets, [5,6]=usdc_value, [7]=timestamp, [8]=status
            shares = int(result[1]) + (int(result[2]) << 128)
            min_assets = int(result[3]) + (int(result[4]) << 128)
            usdc_value = int(result[5]) + (int(result[6]) << 128)
            
            return WithdrawalQueueItem(
                request_id=request_id,
                user=hex(result[0]),
                shares=shares,
                min_assets=min_assets,
                usdc_value=float(usdc_value) / 1e6,
                timestamp=int(result[7]),
                status=WithdrawalStatus(int(result[8]))
            )
        except Exception as e:
            logger.error(f"Failed to get pending withdrawal {request_id}: {e}")
            return None
    
    async def get_status(self) -> dict:
        """Get processor status for API."""
        queue_length = await self._get_withdrawal_queue_length()
        return {
            "running": self.running,
            "pending_count": queue_length,
            "processing_count": len(self.processing_withdrawals),
            "processing_details": {
                str(k): {
                    "usdc_value": v["usdc_value"],
                    "step": v["step"]
                } for k, v in self.processing_withdrawals.items()
            }
        }


# Singleton instance
withdrawal_processor = WithdrawalProcessor()
