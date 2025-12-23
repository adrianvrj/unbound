# For Developers

This guide covers integration with Unbound for developers.

## Contract Addresses (Mainnet)

| Contract | Address |
|----------|---------|
| Vault | `0x066db06cfe7d18c11f6ed5bf93dfb0db7e4ff40d8f5a41e9f7e2d01ebb7e16b8` |
| Operator Wallet | `0x0244f12432e01EC3BE1F4c1E0fbC3e7db90a3EF06105F3568Daab5f1Fdb8ff07` |

## Token Addresses

| Token | Address |
|-------|---------|
| wBTC | `0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac` |
| USDC | `0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8` |

## Backend API

Base URL: `http://localhost:8001` (development)

### Strategy Endpoints

```bash
# Get strategy status
GET /api/strategy/status

# Execute strategy manually
POST /api/strategy/execute

# Open short position
POST /api/strategy/open-short?size_usd=100

# Close position
POST /api/strategy/close

# Start auto-execution loop
POST /api/strategy/start

# Stop auto-execution
POST /api/strategy/stop
```

### Withdrawal Endpoints

```bash
# Get withdrawal status
GET /api/withdrawal/status

# Request withdrawal from Extended
POST /api/withdrawal/request?amount=100

# Prepare vault withdrawal (closes positions)
POST /api/withdrawal/prepare-vault?shares=1000

# Forward USDC to vault
POST /api/withdrawal/forward-to-vault
```

### Wallet Endpoints

```bash
# Get operator wallet status
GET /api/wallet/status

# Start deposit monitor
POST /api/wallet/start-monitor

# Deposit to Extended manually
POST /api/wallet/deposit-to-extended?amount=100
```

## Smart Contract ABI

### Key Functions

```cairo
// Deposit wBTC, receive vault shares
fn deposit(
    amount: u256,
    avnu_calldata: Array<felt252>
) -> u256

// Withdraw shares, receive wBTC
fn withdraw(
    shares: u256,
    receiver: ContractAddress,
    owner: ContractAddress,
    avnu_calldata: Array<felt252>
) -> u256

// Get user's share balance
fn balance_of(owner: ContractAddress) -> u256

// Get total USDC in vault
fn total_assets() -> u256
```

## Frontend Integration

### Connect to Vault

```typescript
import { useContract } from "@starknet-react/core";
import { VAULT_ABI, CONTRACTS } from "@/lib/contracts";

const { contract } = useContract({
    abi: VAULT_ABI,
    address: CONTRACTS.VAULT
});

// Get user shares
const shares = await contract.call("balance_of", [userAddress]);
```

### Get AVNU Swap Calldata

```typescript
import { getSwapCalldata } from "@/lib/avnu";

const calldata = await getSwapCalldata(
    wbtcAmount,
    wbtcAddress,
    usdcAddress,
    userAddress
);
```

## Environment Variables

Backend requires these in `.env`:

```env
# Extended Exchange
EXTENDED_API_KEY=your_api_key
EXTENDED_STARK_KEY=your_stark_private_key
EXTENDED_VAULT_NUMBER=your_position_id

# Operator Wallet
OPERATOR_PRIVATE_KEY=your_starknet_private_key

# Starknet RPC
STARKNET_RPC_URL=https://starknet-mainnet.g.alchemy.com/v2/...

# Vault Contract
VAULT_CONTRACT_ADDRESS=0x066db06cfe7d18c11f6ed5bf93dfb0db7e4ff40d8f5a41e9f7e2d01ebb7e16b8
```

## Running Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values
PYTHONPATH=. uvicorn src.api:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd app
npm install
npm run dev
```

## Testing

### Test Strategy Status

```bash
curl http://localhost:8001/api/strategy/status | jq
```

### Test Deposit Flow

1. Connect wallet on frontend
2. Deposit wBTC
3. Check backend logs for auto-deposit to Extended
4. Verify position on Extended UI
