"""
Deposit Processor Service for Unbound Vault.

Monitors on-chain deposit queue and processes pending deposits by:
1. Detecting new deposit events from the vault contract
2. Depositing USDC to Extended exchange
3. Opening/increasing short position
4. Calling process_deposits() on the vault to mint shares
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from ..config import settings
from ..extended_client import ExtendedClient
from ..starknet_client import StarknetClient

logger = logging.getLogger(__name__)


@dataclass
class DepositQueueItem:
    """Represents a pending deposit from the on-chain queue."""
    request_id: int
    user: str
    receiver: str
    usdc_amount: float
    min_shares: int
    timestamp: int
    processed: bool


class DepositProcessor:
    """
    Processes deposits from the V2 vault queue.
    
    Flow:
    1. Poll vault contract for pending deposits
    2. For each pending deposit:
       a. Transfer USDC from vault to operator wallet (already done by contract)
       b. Deposit USDC to Extended
       c. Open/increase short position
       d. Call process_deposits() on vault to mint shares
    """
    
    def __init__(self):
        self.starknet = StarknetClient()
        self.extended = ExtendedClient()
        self.running = False
        self.last_processed_id = 0
        self.processing_interval = 30  # seconds
        
    async def start(self):
        """Start the deposit processor loop."""
        self.running = True
        logger.info("🏦 Deposit Processor started")
        
        while self.running:
            try:
                await self._process_pending_deposits()
            except Exception as e:
                logger.error(f"Error in deposit processor: {e}")
            
            await asyncio.sleep(self.processing_interval)
    
    async def stop(self):
        """Stop the deposit processor."""
        self.running = False
        logger.info("🏦 Deposit Processor stopped")
    
    async def _process_pending_deposits(self):
        """Process all pending deposits in the queue."""
        # Scan deposits starting from 0, stop when we hit empty slots
        # Cairo Map returns zeros for non-existent keys, so we detect empty by user=0x0
        
        print(f"📥 DepositProcessor: scanning deposits...")
        
        MAX_DEPOSITS = 100  # Safety limit
        
        for request_id in range(MAX_DEPOSITS):
            deposit = await self._get_pending_deposit(request_id)
            
            if deposit is None:
                print(f"   Deposit #{request_id}: error reading")
                continue
            
            # Cairo Map returns zeros for non-existent keys
            # If user is 0x0, this is an empty slot - we've reached the end
            if deposit.user == "0x0":
                print(f"   Deposit #{request_id}: end of queue (empty slot)")
                break
            
            # Skip already processed
            if deposit.processed:
                continue
            
            # Skip invalid/zero deposits  
            if deposit.usdc_amount <= 0.01:
                print(f"   Deposit #{request_id}: skipping zero-amount")
                continue
            
            # Process this deposit
            print(f"   Deposit #{request_id}: usdc_amount=${deposit.usdc_amount:.2f}, processing...")
            await self._process_single_deposit(deposit)

    
    async def _get_deposit_queue_length(self) -> int:
        """Get the number of pending deposits from the vault."""
        try:
            # Call vault.get_deposit_queue_length()
            result = await self.starknet.call_contract(
                settings.vault_contract_address,
                "get_deposit_queue_length",
                []
            )
            return int(result[0]) if result else 0
        except Exception as e:
            logger.error(f"Failed to get deposit queue length: {e}")
            return 0
    
    async def _get_pending_deposit(self, request_id: int) -> Optional[DepositQueueItem]:
        """Get a specific pending deposit from the vault."""
        try:
            result = await self.starknet.call_contract(
                settings.vault_contract_address,
                "get_pending_deposit",
                [request_id],
                u256_indices=[0]  # request_id is u256
            )
            
            if not result:
                return None
            
            # Parse the deposit request struct
            # u256 values serialize as 2 felts (low, high)
            # Order: user[0], receiver[1], usdc_amount[2,3], min_shares[4,5], timestamp[6], processed[7]
            usdc_amount_raw = int(result[2]) + (int(result[3]) << 128)
            min_shares_raw = int(result[4]) + (int(result[5]) << 128)
            
            return DepositQueueItem(
                request_id=request_id,
                user=hex(result[0]),
                receiver=hex(result[1]),
                usdc_amount=float(usdc_amount_raw) / 1e6,  # USDC has 6 decimals
                min_shares=min_shares_raw,
                timestamp=int(result[6]),
                processed=bool(result[7])
            )
        except Exception as e:
            logger.error(f"Failed to get pending deposit {request_id}: {e}")
            return None
    
    async def _process_single_deposit(self, deposit: DepositQueueItem) -> bool:
        """
        Process a single deposit:
        1. Call process_deposits() on vault (transfers USDC to operator, mints shares)
        2. Deposit USDC to Extended
        3. Open/increase short position
        """
        logger.info(f"Processing deposit #{deposit.request_id}: ${deposit.usdc_amount:.2f} USDC")
        
        try:
            # Step 1: Call process_deposits() on vault
            # This transfers USDC to operator and mints shares to user
            process_result = await self.starknet.invoke_contract(
                settings.vault_contract_address,
                "process_deposits",
                [1]  # Process 1 deposit at a time
            )
            
            if not process_result:
                logger.error("Failed to call process_deposits on vault")
                return False
            
            logger.info(f"✅ Processed deposit #{deposit.request_id}, shares minted, USDC transferred to operator")
            
            # Wait a bit for the transaction to be confirmed
            await asyncio.sleep(5)
            
            # Step 2: Get operator's USDC balance (should now have the USDC from vault)
            # Note: usdc_amount is TOTAL value (2x), but actual USDC received is half
            actual_usdc = deposit.usdc_amount / 2
            operator_usdc = await self.starknet.get_usdc_balance()
            
            if operator_usdc < actual_usdc * 0.9:  # Allow some tolerance
                logger.warning(f"Expected USDC not received yet. Have: ${operator_usdc:.2f}, Expected: ${actual_usdc:.2f}")
                # Continue anyway - USDC might arrive later
            
            # Step 3: Deposit USDC to Extended using AutoDepositor
            # Only deposit the actual USDC received (half of total value)
            from ..starknet_client import AutoDepositor
            depositor = AutoDepositor()
            deposit_result = await depositor.deposit_to_extended(actual_usdc)
            if deposit_result:
                logger.info(f"✅ Deposited ${actual_usdc:.2f} to Extended, TX: {deposit_result}")
            else:
                logger.warning("Extended deposit may have failed, but shares already minted")
            
            # Step 4: Open/increase short position
            # Short position is based on actual USDC deposited, not total value
            position_result = await self.extended.open_short_position(
                settings.market,
                actual_usdc * settings.leverage
            )
            
            if position_result:
                logger.info(f"✅ Opened short position: ${actual_usdc * settings.leverage:.2f}")
            else:
                logger.warning("Short position may have failed, but continuing...")
            
            return True
                
        except Exception as e:
            logger.error(f"Error processing deposit #{deposit.request_id}: {e}")
            return False
    
    async def get_status(self) -> dict:
        """Get processor status for API."""
        queue_length = await self._get_deposit_queue_length()
        return {
            "running": self.running,
            "last_processed_id": self.last_processed_id,
            "pending_count": queue_length,
            "processing_interval": self.processing_interval
        }


# Singleton instance
deposit_processor = DepositProcessor()
