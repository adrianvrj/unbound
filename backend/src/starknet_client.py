"""
Starknet on-chain client for the Funding Rate Vault.
Monitors USDC balance and auto-deposits to Extended.
"""
import asyncio
from typing import Optional
import aiohttp
try:
    from .config import settings
except ImportError:
    from src.config import settings

# Starknet RPC URL
STARKNET_RPC = "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_10/dql5pMT88iueZWl7L0yzT56uVk0EBU4L"

# Contract addresses
USDC_ADDRESS = settings.usdc_contract
EXTENDED_DEPOSIT = settings.extended_deposit_contract
OPERATOR_WALLET = settings.operator_address


class StarknetClient:
    """Client for Starknet on-chain operations."""
    
    def __init__(self, rpc_url: str = STARKNET_RPC):
        self.rpc_url = rpc_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        if self._session:
            await self._session.close()
    
    async def _rpc_call(self, method: str, params: dict) -> dict:
        """Make an RPC call to Starknet."""
        await self._ensure_session()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        async with self._session.post(self.rpc_url, json=payload) as resp:
            data = await resp.json()
            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")
            return data.get("result", {})
    
    async def get_usdc_balance(self, address: str = None) -> float:
        """Get USDC balance of an address."""
        if address is None:
            address = OPERATOR_WALLET
        try:
            # balance_of selector
            selector = "0x02e4263afad30923c891518314c3c95dbe830a16874e8abc5777a9a20b54c76e"
            result = await self._rpc_call("starknet_call", {
                "request": {
                    "contract_address": USDC_ADDRESS,
                    "entry_point_selector": selector,
                    "calldata": [address]
                },
                "block_id": "latest"
            })
            
            if result and len(result) >= 1:
                balance_low = int(result[0], 16) if isinstance(result[0], str) else result[0]
                balance_high = int(result[1], 16) if len(result) > 1 and isinstance(result[1], str) else 0
                balance_raw = balance_low + (balance_high << 128)
                return balance_raw / 1e6
            return 0.0
        except Exception as e:
            print(f"Error getting USDC balance: {e}")
            return 0.0

    async def get_nonce(self, address: str = None) -> int:
        """Get current nonce for an account."""
        if address is None:
            address = OPERATOR_WALLET
        try:
            result = await self._rpc_call("starknet_getNonce", {
                "contract_address": address,
                "block_id": "latest"
            })
            return int(result, 16) if isinstance(result, str) else result
        except Exception as e:
            print(f"Error getting nonce: {e}")
            return 0

    async def get_vault_total_usdc(self) -> float:
        """Get total USDC deposited in the vault from contract state."""
        try:
            # get_total_usdc_deposited selector
            selector = "0x9a981d64b567ea8f589860cbfe910b5e3ae2fe1227c911530440f5e6036129"
            result = await self._rpc_call("starknet_call", {
                "request": {
                    "contract_address": settings.vault_contract_address,
                    "entry_point_selector": selector,
                    "calldata": []
                },
                "block_id": "latest"
            })
            
            if result and len(result) >= 1:
                val_low = int(result[0], 16) if isinstance(result[0], str) else result[0]
                val_high = int(result[1], 16) if len(result) > 1 and isinstance(result[1], str) else 0
                val_raw = val_low + (val_high << 128)
                return val_raw / 1e6
            return 0.0
        except Exception as e:
            print(f"Error getting vault total USDC: {e}")
            return 0.0

    async def get_vault_total_shares(self) -> float:
        """Get total shares (total_supply) of the vault."""
        try:
            # total_supply selector
            selector = "0x1557182e4359a1f0c6301278e8f5b35a776ab58d39892581e357578fb287836"
            result = await self._rpc_call("starknet_call", {
                "request": {
                    "contract_address": settings.vault_contract_address,
                    "entry_point_selector": selector,
                    "calldata": []
                },
                "block_id": "latest"
            })
            
            if result and len(result) >= 1:
                val_low = int(result[0], 16) if isinstance(result[0], str) else result[0]
                val_high = int(result[1], 16) if len(result) > 1 and isinstance(result[1], str) else 0
                val_raw = val_low + (val_high << 128)
                return val_raw / 1e6 # Vault shares match USDC decimals (6)
            return 0.0
        except Exception as e:
            print(f"Error getting vault total shares: {e}")
            return 0.0

    async def get_vault_wbtc_held(self) -> float:
        """Get wBTC held in vault as LONG exposure for delta-neutral strategy."""
        try:
            # get_wbtc_held selector - computed from starknet_keccak("get_wbtc_held")
            from starknet_py.hash.selector import get_selector_from_name
            selector = hex(get_selector_from_name("get_wbtc_held"))
            
            result = await self._rpc_call("starknet_call", {
                "request": {
                    "contract_address": settings.vault_contract_address,
                    "entry_point_selector": selector,
                    "calldata": []
                },
                "block_id": "latest"
            })
            
            if result and len(result) >= 1:
                val_low = int(result[0], 16) if isinstance(result[0], str) else result[0]
                val_high = int(result[1], 16) if len(result) > 1 and isinstance(result[1], str) else 0
                val_raw = val_low + (val_high << 128)
                return val_raw / 1e8  # wBTC has 8 decimals
            return 0.0
        except Exception as e:
            print(f"Error getting vault wBTC held: {e}")
            return 0.0

    def _serialize_u256(self, value: int) -> list:
        """
        Serialize a u256 value into two felts (low, high) for Cairo.
        Cairo u256 = { low: u128, high: u128 }
        """
        low = value & ((1 << 128) - 1)  # Lower 128 bits
        high = value >> 128  # Upper 128 bits
        return [hex(low), hex(high)]

    async def call_contract(self, contract_address: str, function_name: str, calldata: list, u256_indices: list = None) -> list:
        """
        Call a contract view function.
        Returns the raw result array.
        
        Args:
            contract_address: Contract to call
            function_name: Entry point name
            calldata: Parameters (integers will be converted to hex)
            u256_indices: List of indices in calldata that are u256 values (need to be split into low/high)
        """
        try:
            # Compute selector from function name using starknet_keccak
            selector = self._get_function_selector(function_name)
            
            # Build calldata with proper u256 serialization
            calldata_hex = []
            u256_set = set(u256_indices or [])
            
            for i, c in enumerate(calldata):
                if i in u256_set:
                    # Serialize as u256 (two felts: low, high)
                    val = int(c) if isinstance(c, str) else c
                    calldata_hex.extend(self._serialize_u256(val))
                else:
                    calldata_hex.append(hex(c) if isinstance(c, int) else c)
            
            result = await self._rpc_call("starknet_call", {
                "request": {
                    "contract_address": contract_address,
                    "entry_point_selector": selector,
                    "calldata": calldata_hex
                },
                "block_id": "latest"
            })
            
            if result:
                # Convert hex results to integers
                return [int(r, 16) if isinstance(r, str) else r for r in result]
            return []
        except Exception as e:
            print(f"Error calling contract {function_name}: {e}")
            return []

    async def invoke_contract(self, contract_address: str, function_name: str, calldata: list, u256_indices: list = None):
        """
        Invoke a contract function (requires signing).
        Uses AutoDepositor's account for signing.
        
        Args:
            u256_indices: List of indices in calldata that are u256 values (need to be split into low/high)
        """
        try:
            from starknet_py.net.account.account import Account
            from starknet_py.net.full_node_client import FullNodeClient
            from starknet_py.net.signer.stark_curve_signer import KeyPair
            from starknet_py.net.models import StarknetChainId
            from starknet_py.contract import Contract
            
            # Create account
            client = FullNodeClient(node_url=settings.starknet_rpc_url)
            key_pair = KeyPair.from_private_key(int(settings.operator_private_key, 16))
            account = Account(
                client=client,
                address=settings.operator_address,
                key_pair=key_pair,
                chain=StarknetChainId.MAINNET
            )
            
            # Compute selector
            selector = self._get_function_selector(function_name)
            
            # Serialize calldata with u256 support
            serialized_calldata = []
            u256_set = set(u256_indices or [])
            
            for i, c in enumerate(calldata):
                if i in u256_set:
                    # Serialize as u256 (two felts: low, high)
                    val = int(c) if isinstance(c, str) else c
                    low = val & ((1 << 128) - 1)
                    high = val >> 128
                    serialized_calldata.extend([low, high])
                else:
                    serialized_calldata.append(c)
            
            # Execute call using starknet_py Call object
            from starknet_py.net.client_models import Call
            call = Call(
                to_addr=int(contract_address, 16),
                selector=int(selector, 16),
                calldata=serialized_calldata
            )
            
            result = await account.execute_v3(calls=[call], auto_estimate=True)
            # Wait for transaction acceptance (starknet_py v0.23+)
            await client.wait_for_tx(result.transaction_hash)
            
            return hex(result.transaction_hash)
        except Exception as e:
            print(f"Error invoking contract {function_name}: {e}")
            return None

    def _get_function_selector(self, function_name: str) -> str:
        """
        Get the selector for a function name using starknet_keccak.
        Selector = starknet_keccak(function_name) mod FIELD_PRIME
        """
        from starknet_py.hash.selector import get_selector_from_name
        selector = get_selector_from_name(function_name)
        return hex(selector)


class AutoDepositor:
    """
    Auto-deposits USDC to Extended when detected in operator wallet.
    Uses starknet.py for transaction signing.
    """
    
    def __init__(self):
        self.starknet = StarknetClient()
        self.last_balance = 0.0
        self.min_deposit_amount = 1.0  # Min $1 USDC to trigger deposit
        self._starknet_account = None
    
    async def _get_account(self):
        """Get or create starknet account for signing."""
        if self._starknet_account is None:
            try:
                from starknet_py.net.account.account import Account
                from starknet_py.net.full_node_client import FullNodeClient
                from starknet_py.net.models import StarknetChainId
                from starknet_py.net.signer.stark_curve_signer import KeyPair
                
                if not settings.operator_private_key:
                    print("⚠️ No operator private key configured - cannot auto-deposit")
                    return None
                
                client = FullNodeClient(node_url=STARKNET_RPC)
                key_pair = KeyPair.from_private_key(int(settings.operator_private_key, 16))
                
                self._starknet_account = Account(
                    address=int(OPERATOR_WALLET, 16),
                    client=client,
                    key_pair=key_pair,
                    chain=StarknetChainId.MAINNET
                )
                print("✅ Starknet account initialized for auto-deposit")
            except ImportError:
                print("⚠️ starknet-py not installed. Run: pip install starknet-py")
                return None
            except Exception as e:
                print(f"❌ Error initializing account: {e}")
                return None
        
        if self._starknet_account:
            # Refresh nonce from network in case external txs were sent (like sncast)
            try:
                await self._starknet_account.get_nonce()
            except:
                pass
                
        return self._starknet_account
    
    async def deposit_to_extended(self, amount_usdc: float) -> Optional[str]:
        """
        Deposit USDC to Extended deposit contract.
        Requires: approve USDC, then call deposit(position_id, quantized_amount, salt)
        Returns transaction hash if successful.
        """
        account = await self._get_account()
        if account is None:
            return None
        
        try:
            from starknet_py.net.client_models import Call
            import random
            
            # Get vault number from settings
            vault_number = settings.extended_vault_number
            if not vault_number:
                print("❌ No EXTENDED_VAULT_NUMBER configured!")
                return None
            
            # Amount in raw units (6 decimals for USDC)
            amount_raw = int(amount_usdc * 1e6)
            
            # Generate random salt
            salt = random.randint(1, 2**64 - 1)
            
            print(f"📤 Depositing ${amount_usdc:.2f} USDC to Extended...")
            print(f"   Position ID (vault): {vault_number}")
            print(f"   Amount (raw): {amount_raw}")
            print(f"   Salt: {salt}")
            
            # Step 1: Approve USDC to Extended contract
            # approve selector = 0x0219209e083275171774dab1df80982e9df2096516f06319c5c6d71ae0a8480c
            approve_call = Call(
                to_addr=int(USDC_ADDRESS, 16),
                selector=0x0219209e083275171774dab1df80982e9df2096516f06319c5c6d71ae0a8480c,  # approve
                calldata=[
                    int(EXTENDED_DEPOSIT, 16),  # spender
                    amount_raw,  # amount low
                    0  # amount high
                ]
            )
            
            # Step 2: Call deposit on Extended contract
            # deposit(position_id, quantized_amount, salt)
            # deposit selector = get_selector_from_name("deposit")
            # deposit selector = 0x00c73f681176fc7b3f9693986fd7b14581e8d540519e27400e88b8713932be01
            deposit_call = Call(
                to_addr=int(EXTENDED_DEPOSIT, 16),
                selector=0x00c73f681176fc7b3f9693986fd7b14581e8d540519e27400e88b8713932be01,  # deposit
                calldata=[
                    int(vault_number),  # position_id (vault number)
                    amount_raw,  # quantized_amount
                    salt  # salt
                ]
            )
            
            # Execute both calls in single tx
            result = await account.execute_v3(
                calls=[approve_call, deposit_call],
                auto_estimate=True
            )
            tx_hash = hex(result.transaction_hash)
            
            print(f"✅ Deposit TX sent: {tx_hash}")
            print(f"   View: https://voyager.online/tx/{tx_hash}")
            
            # Wait for confirmation
            await account.client.wait_for_tx(result.transaction_hash)
            print(f"✅ Deposit confirmed!")
            
            return tx_hash
            
        except Exception as e:
            print(f"❌ Deposit failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def send_usdc_to_vault(self, amount_usdc: float, vault_address: str) -> Optional[str]:
        """
        Send USDC from operator wallet to vault contract.
        Used for withdrawals - vault needs USDC to swap back to wBTC.
        
        Args:
            amount_usdc: Amount of USDC to send
            vault_address: Address of the vault contract
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        account = await self._get_account()
        if account is None:
            return None
        
        try:
            from starknet_py.net.client_models import Call
            
            amount_raw = int(amount_usdc * 1e6)
            
            print(f"📤 Sending ${amount_usdc:.2f} USDC to vault...")
            print(f"   Vault: {vault_address}")
            
            # Simple USDC transfer to vault
            transfer_call = Call(
                to_addr=int(USDC_ADDRESS, 16),
                selector=0x83afd3f4caedc6eebf44246fe54e38c95e3179a5ec9ea81740eca5b482d12e,  # transfer
                calldata=[
                    int(vault_address, 16),  # recipient (vault)
                    amount_raw,  # amount low
                    0  # amount high
                ]
            )
            
            result = await account.execute_v3(
                calls=[transfer_call],
                auto_estimate=True
            )
            tx_hash = hex(result.transaction_hash)
            
            print(f"✅ Transfer TX sent: {tx_hash}")
            print(f"   View: https://voyager.online/tx/{tx_hash}")
            
            await account.client.wait_for_tx(result.transaction_hash)
            print(f"✅ Transfer confirmed!")
            
            return tx_hash
            
        except Exception as e:
            print(f"❌ Transfer to vault failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def sync_vault_nav(self, equity: float) -> Optional[str]:
        """
        Sync the vault's on-chain NAV with the actual equity on Extended.
        This ensures users get their fair share of yield when withdrawing.
        """
        account = await self._get_account()
        if account is None:
            return None
        
        try:
            from starknet_py.net.client_models import Call
            
            # Amount in raw units (6 decimals for USDC)
            equity_raw = int(equity * 1e6)
            
            print(f"🔄 Syncing vault NAV: ${equity:.2f} USDC...")
            
            # Call update_nav(equity)
            # selector = 0x27e833fe155ab45b4e8ee354ef7ebfe9ce15012c4f81e399a69a8a7ec6c1d94
            nav_call = Call(
                to_addr=int(settings.vault_contract_address, 16),
                selector=0x27e833fe155ab45b4e8ee354ef7ebfe9ce15012c4f81e399a69a8a7ec6c1d94,
                calldata=[
                    equity_raw,  # amount low
                    0  # amount high
                ]
            )
            
            result = await account.execute_v3(
                calls=[nav_call],
                auto_estimate=True
            )
            tx_hash = hex(result.transaction_hash)
            
            print(f"✅ NAV Sync TX sent: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            print(f"❌ NAV Sync failed: {e}")
            return None
    
    async def check_and_deposit(self) -> dict:
        """
        Check for new USDC and auto-deposit to Extended.
        Returns status dict.
        """
        current_balance = await self.starknet.get_usdc_balance()
        
        result = {
            "current_balance": current_balance,
            "last_balance": self.last_balance,
            "deposited": False,
            "tx_hash": None
        }
        
        # Check if balance increased significantly
        new_deposit = current_balance - self.last_balance
        if new_deposit >= self.min_deposit_amount:
            print(f"💰 Detected new deposit: ${new_deposit:.2f} USDC")
            
            # Deposit to Extended
            tx_hash = await self.deposit_to_extended(new_deposit)
            if tx_hash:
                result["deposited"] = True
                result["tx_hash"] = tx_hash
                result["amount_deposited"] = new_deposit
        
        self.last_balance = await self.starknet.get_usdc_balance()  # Update after deposit
        return result


class VaultMonitor:
    """
    Monitors the operator wallet for:
    1. Incoming USDC from the vault -> auto-deposit to Extended
    2. Incoming USDC from Extended -> auto-forward to vault
    """
    
    def __init__(self):
        self.starknet = StarknetClient()
        self.depositor = AutoDepositor()
        self.last_balance = 0.0
        self.pending_deposit = 0.0
        self.pending_withdrawal_amount = 0.0
        self.running = False
        self.persistence_file = "vault_monitor_state.json"
        self._load_state()
    
    def _save_state(self):
        """Save monitor state to disk."""
        import json
        try:
            state = {
                "pending_deposit": self.pending_deposit,
                "pending_withdrawal_amount": self.pending_withdrawal_amount,
                "last_balance": self.last_balance
            }
            with open(self.persistence_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"⚠️ Failed to save monitor state: {e}")

    def _load_state(self):
        """Load monitor state from disk."""
        import json
        import os
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, "r") as f:
                    state = json.load(f)
                    self.pending_deposit = state.get("pending_deposit", 0.0)
                    self.pending_withdrawal_amount = state.get("pending_withdrawal_amount", 0.0)
                    self.last_balance = state.get("last_balance", 0.0)
                print(f"📦 Loaded monitor state: Pending Deposit=${self.pending_deposit:.2f}, Pending Withdrawal=${self.pending_withdrawal_amount:.2f}")
        except Exception as e:
            print(f"⚠️ Failed to load monitor state: {e}")

    def expect_withdrawal(self, amount: float):
        """Register an expected withdrawal from Extended."""
        self.pending_withdrawal_amount += amount
        self._save_state()
        print(f"⏳ Expecting withdrawal from Extended: ${amount:.2f}")

    async def check_for_balance_changes(self) -> float:
        """Check for balance changes and categorize them."""
        current_balance = await self.starknet.get_usdc_balance()
        
        # If we have pending withdrawals and some balance, try to forward it
        # even if no "increase" was detected (e.g. server restarted after funds arrived)
        if self.pending_withdrawal_amount > 0 and current_balance > 0.1:
            # We have some money in operator wallet and we're expecting a withdrawal.
            # Forward what we have (up to the pending amount)
            amount_to_forward = min(current_balance, self.pending_withdrawal_amount)
            print(f"🚀 Detected available funds for pending withdrawal: ${amount_to_forward:.2f}")
            
            tx_hash = await self.depositor.send_usdc_to_vault(amount_to_forward, settings.vault_contract_address)
            if tx_hash:
                self.pending_withdrawal_amount -= amount_to_forward
                self.last_balance = max(0, current_balance - amount_to_forward)
                self._save_state()
                return amount_to_forward
        
        if current_balance > self.last_balance:
            increase = current_balance - self.last_balance
            print(f"💰 USDC increase detected: ${increase:.2f}")
            
            # Simple heuristic: if we have pending withdrawals, this might be one
            if self.pending_withdrawal_amount > 0:
                withdrawal_match = min(increase, self.pending_withdrawal_amount)
                print(f"   Assuming ${withdrawal_match:.2f} is withdrawal from Extended")
                
                # Auto-forward to vault
                tx_hash = await self.depositor.send_usdc_to_vault(withdrawal_match, settings.vault_contract_address)
                if tx_hash:
                    self.pending_withdrawal_amount -= withdrawal_match
                    increase -= withdrawal_match
            
            # Anything left is considered a new deposit to be sent to Extended
            if increase > 0.1: # Threshold for rounding
                print(f"   Assuming ${increase:.2f} is new deposit from vault")
                self.pending_deposit += increase
            
            self.last_balance = current_balance
            self._save_state()
            return increase
        
        self.last_balance = current_balance
        # Note: if balance decreased, we just update last_balance
        return 0.0
    
    async def auto_deposit_if_pending(self) -> Optional[str]:
        """Auto-deposit pending USDC to Extended and execute strategy."""
        if self.pending_deposit >= 1.0:  # Min $1
            tx_hash = await self.depositor.deposit_to_extended(self.pending_deposit)
            if tx_hash:
                self.pending_deposit = 0.0
                
                # Execute strategy immediately after deposit
                print("🤖 Executing strategy after deposit...")
                try:
                    from .strategy import UnboundVaultStrategy
                    from .extended_client import ExtendedClient
                    
                    strategy = UnboundVaultStrategy(ExtendedClient())
                    result = await strategy.execute_strategy()
                    print(f"   Strategy result: {result['action']}")
                    if result.get('status') == 'success':
                        print(f"   ✅ {result['action']} executed successfully!")
                except Exception as e:
                    print(f"   ⚠️ Strategy execution failed: {e}")
                
            return tx_hash
        return None
    
    async def run_monitor(self, interval_seconds: int = 60, auto_process: bool = True):
        """
        Run the monitor loop.
        Checks for balance changes and auto-processes deposits/withdrawals.
        """
        self.running = True
        print(f"🔍 Starting vault monitor (checking every {interval_seconds}s)")
        
        # Get initial balance
        self.last_balance = await self.starknet.get_usdc_balance()
        print(f"   Initial USDC balance: ${self.last_balance:.2f}")
        
        while self.running:
            try:
                await self.check_for_balance_changes()
                
                if auto_process:
                    if self.pending_deposit >= 1.0:
                        await self.auto_deposit_if_pending()
                    
                    # Update state periodically just in case
                    self._save_state()
                    
            except Exception as e:
                print(f"Monitor error: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    def stop(self):
        """Stop the monitor."""
        self.running = False
        print("🛑 Vault monitor stopped")


# Global instances
auto_depositor = AutoDepositor()
vault_monitor = VaultMonitor()


async def test_starknet():
    """Test Starknet connection."""
    client = StarknetClient()
    try:
        balance = await client.get_usdc_balance()
        print(f"✅ Operator wallet USDC balance: ${balance:.2f}")
        return balance
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_starknet())
