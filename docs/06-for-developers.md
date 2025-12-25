# For Developers

This guide covers integration with Unbound's delta-neutral vault for developers.

## Contract Addresses (Mainnet)

| Contract | Address |
|----------|---------|
| UnboundVault | `0x0291a1d4829bf8852aa5182409cc5b5f7c15a2709a5e5a5ff8e44791996acb62` |
| Operator | `0x0244f12432e01EC3BE1F4c1E0fbC3e7db90a3EF06105F3568Daab5f1Fdb8ff07` |

## Token Addresses

| Token | Address |
|-------|---------|
| wBTC | `0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac` |
| USDC | `0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8` |

---

## Smart Contract Integration

### Vault ABI (Key Functions)

```cairo
// Queue a deposit (user calls this)
fn deposit(
    wbtc_amount: u256,
    min_shares: u256,
    avnu_calldata: Array<felt252>
) -> u256  // Returns request_id

// Request withdrawal (user calls this)
fn request_withdraw(
    shares: u256,
    min_assets: u256
) -> u256  // Returns request_id

// Complete withdrawal after it's ready (user calls this)
fn complete_withdrawal(
    request_id: u256,
    avnu_calldata: Array<felt252>
)

// Read user's share balance
fn balance_of(owner: ContractAddress) -> u256

// Read total shares
fn total_supply() -> u256

// Get vault NAV (for calculating share price)
fn get_total_nav() -> u256
```

### Reading User Position

```typescript
import { Contract, RpcProvider } from "starknet";

const provider = new RpcProvider({ nodeUrl: RPC_URL });
const vault = new Contract(VAULT_ABI, VAULT_ADDRESS, provider);

// Get user shares
const shares = await vault.balance_of(userAddress);

// Get total NAV and calculate share value
const totalNav = await vault.get_total_nav();
const totalShares = await vault.total_supply();
const shareValue = totalNav / totalShares;
const userValue = shares * shareValue;
```

### Deposit Example (Frontend)

```typescript
import { useAccount, useContract } from "@starknet-react/core";
import { getSwapCalldata } from "@/lib/avnu";

async function deposit(wbtcAmount: bigint) {
    const { account } = useAccount();
    
    // Get AVNU swap calldata for 50% wBTC → USDC
    const swapCalldata = await getSwapCalldata(
        WBTC_ADDRESS,
        USDC_ADDRESS,
        wbtcAmount / 2n,  // Only 50% gets swapped
        VAULT_ADDRESS,
        1  // 1% slippage
    );
    
    // Approve wBTC transfer
    const approveCall = {
        contractAddress: WBTC_ADDRESS,
        entrypoint: "approve",
        calldata: [VAULT_ADDRESS, wbtcAmount, 0]
    };
    
    // Deposit call
    const depositCall = {
        contractAddress: VAULT_ADDRESS,
        entrypoint: "deposit",
        calldata: [wbtcAmount, 0, minShares, 0, ...swapCalldata]
    };
    
    return account.execute([approveCall, depositCall]);
}
```

### Reading Pending Withdrawals

```typescript
async function getUserWithdrawals(userAddress: string) {
    const queueLength = await vault.get_withdrawal_queue_length();
    const withdrawals = [];
    
    for (let i = 0; i < queueLength; i++) {
        const withdrawal = await vault.get_pending_withdrawal(i);
        if (withdrawal.user === userAddress) {
            withdrawals.push({
                requestId: i,
                shares: withdrawal.shares,
                usdcValue: withdrawal.usdc_amount,
                status: withdrawal.status  // 0=PENDING, 2=READY, 3=COMPLETED
            });
        }
    }
    return withdrawals;
}
```

---

## Backend API

Base URL: `https://api.unbound.finance` (production) or `http://localhost:8001` (dev)

### Public Endpoints

```bash
# Get vault status (NAV, delta, positions)
GET /api/status

# Get current APY and funding rate
GET /api/apy

# Response includes Extended's exact formula:
{
    "current_funding_rate": 0.000013,
    "hourly_rate_percent": "0.0013%",
    "estimated_apy_2x": 22.78,
    "position_size_btc": 0.057,
    "mark_price": 88000,
    "hourly_funding_payment_usd": 0.065,
    "annual_funding_payment_usd": 570
}

# Get funding payment history
GET /api/funding-history?limit=50

# Get queue status
GET /api/queues/status
```

### Strategy Endpoints (Admin)

```bash
# Get strategy state
GET /api/strategy/status

# Execute strategy once
POST /api/strategy/execute

# Manual position control
POST /api/strategy/open-short?size_usd=1000
POST /api/strategy/close
```

---

## Integrating with Your Frontend

### 1. Install Dependencies

```bash
npm install starknet @starknet-react/core
```

### 2. Setup Provider

```typescript
import { StarknetConfig, publicProvider } from "@starknet-react/core";

function App() {
    return (
        <StarknetConfig chains={[mainnet]} provider={publicProvider()}>
            <YourApp />
        </StarknetConfig>
    );
}
```

### 3. Use Vault Hooks

```typescript
import { useContractRead } from "@starknet-react/core";

function VaultStats() {
    const { data: nav } = useContractRead({
        address: VAULT_ADDRESS,
        abi: VAULT_ABI,
        functionName: "get_total_nav"
    });
    
    const { data: apy } = useSWR("/api/apy", fetcher);
    
    return (
        <div>
            <p>Total NAV: ${nav}</p>
            <p>APY: {apy?.estimated_apy_2x}%</p>
        </div>
    );
}
```

---

## Running Your Own Instance

### Environment Variables

```env
# Extended Exchange
EXTENDED_API_KEY=your_api_key
EXTENDED_STARK_KEY=your_stark_private_key
EXTENDED_VAULT_NUMBER=your_position_id

# Operator Wallet (for processing deposits/withdrawals)
OPERATOR_ADDRESS=0x...
OPERATOR_PRIVATE_KEY=your_starknet_private_key

# Starknet RPC
STARKNET_RPC_URL=https://starknet-mainnet.g.alchemy.com/v2/...

# Vault Contract
VAULT_CONTRACT_ADDRESS=0x0291a1d4829bf8852aa5182409cc5b5f7c15a2709a5e5a5ff8e44791996acb62
```

### Start Backend

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. uvicorn src.api:app --host 0.0.0.0 --port 8001
```

This starts:
- `DepositProcessor` - polls vault queue, deposits to Extended
- `WithdrawalProcessor` - processes withdrawals from Extended
- `PositionManager` - monitors funding rate, closes if negative
- `NAVReporter` - reports NAV to vault contract

---

## Webhook Events (Coming Soon)

Subscribe to vault events:

```typescript
// Deposit confirmed
{ event: "DEPOSIT_PROCESSED", requestId: 5, shares: 1000 }

// Withdrawal ready
{ event: "WITHDRAWAL_READY", requestId: 3, usdcAmount: 2500 }

// Funding payment received
{ event: "FUNDING_RECEIVED", amount: 0.65, timestamp: 1703520000 }
```

---

## Support

- GitHub: [github.com/unbound-finance/unbound](https://github.com/unbound-finance/unbound)
- Discord: Coming soon
- Email: dev@unbound.finance
