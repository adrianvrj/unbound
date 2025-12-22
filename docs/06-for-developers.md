# For Developers

This guide covers how to integrate with or build on top of Unbound.

## Contract Addresses (Mainnet)

```typescript
const CONTRACTS = {
    VAULT: "0x03ca2746d882bfc63213dc264af5e0856e91c393f07c966607cc1492cec55aa9",
    EXECUTOR: "0x0208e65dcda65cf743a42132fa5c7587a67a49cf990155ab3646d13939ee8848",
    
    // External
    VESU_POOL: "0x0451fe483d5921a2919ddd81d0de6696669bccdacd859f72a4fba7656b97c3b5",
    AVNU_ROUTER: "0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f",
    
    // Tokens
    WBTC: "0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac",
    USDC: "0x033068f6539f8e6e6b131e6b2b814e6c34a5224bc66947c47dab9dfee93b35fb",
};
```

## ABIs

### Vault ABI (Key Functions)

```json
[
    {
        "name": "deposit_and_leverage",
        "type": "function",
        "inputs": [
            {"name": "assets", "type": "u256"},
            {"name": "flash_loan_amount", "type": "u256"},
            {"name": "min_collateral_out", "type": "u256"},
            {"name": "avnu_calldata", "type": "Array<felt252>"}
        ],
        "outputs": [{"type": "u256"}],
        "state_mutability": "external"
    },
    {
        "name": "withdraw_all",
        "type": "function",
        "inputs": [
            {"name": "min_underlying_out", "type": "u256"},
            {"name": "avnu_calldata", "type": "Array<felt252>"}
        ],
        "outputs": [{"type": "u256"}],
        "state_mutability": "external"
    },
    {
        "name": "get_vault_position",
        "type": "function",
        "inputs": [],
        "outputs": [{"type": "(u256, u256)"}],
        "state_mutability": "view"
    },
    {
        "name": "total_assets",
        "type": "function",
        "inputs": [],
        "outputs": [{"type": "u256"}],
        "state_mutability": "view"
    }
]
```

## Integration Guide

### 1. Prerequisites

- Node.js 18+
- starknet.js v6+
- Access to Starknet RPC

### 2. Reading Vault State

```typescript
import { Contract, RpcProvider } from 'starknet';
import { VAULT_ABI, CONTRACTS } from './contracts';

const provider = new RpcProvider({ nodeUrl: 'YOUR_RPC_URL' });
const vault = new Contract(VAULT_ABI, CONTRACTS.VAULT, provider);

// Get total assets in vault
const totalAssets = await vault.total_assets();
console.log('Total Assets:', totalAssets.toString());

// Get vault position (collateral, debt)
const [collateral, debt] = await vault.get_vault_position();
console.log('Collateral:', collateral.toString());
console.log('Debt:', debt.toString());

// Calculate leverage ratio
const leverage = Number(collateral) / (Number(collateral) - Number(debt) * 1e2);
```

### 3. Opening a Position

```typescript
import { Account, CallData, cairo } from 'starknet';

// Step 1: Get AVNU quote for swap
const avnuQuote = await fetch('https://starknet.api.avnu.fi/swap/v2/quotes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        sellTokenAddress: CONTRACTS.USDC,
        buyTokenAddress: CONTRACTS.WBTC,
        sellAmount: flashLoanAmount.toString(),
        takerAddress: CONTRACTS.EXECUTOR,
    })
});

// Step 2: Build swap calldata
const swapCalldata = await fetch('https://starknet.api.avnu.fi/swap/v2/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        quoteId: avnuQuote.quoteId,
        takerAddress: CONTRACTS.EXECUTOR,
        slippage: 0.01,
    })
});

// Step 3: Build transaction
const depositAmount = BigInt(0.001 * 1e8); // 0.001 wBTC
const flashAmount = BigInt(100 * 1e6);      // $100 USDC

const calls = [
    // Approve wBTC to vault
    {
        contractAddress: CONTRACTS.WBTC,
        entrypoint: 'approve',
        calldata: CallData.compile([
            CONTRACTS.VAULT,
            cairo.uint256(depositAmount)
        ])
    },
    // Deposit with leverage
    {
        contractAddress: CONTRACTS.VAULT,
        entrypoint: 'deposit_and_leverage',
        calldata: [
            ...cairo.uint256(depositAmount),
            ...cairo.uint256(flashAmount),
            ...cairo.uint256(0),  // min_collateral_out
            swapCalldata.calls[0].calldata.length.toString(16),
            ...swapCalldata.calls[0].calldata
        ]
    }
];

const tx = await account.execute(calls);
```

### 4. Querying User Position

```typescript
// Get user's share balance
const shares = await vault.balance_of(userAddress);

// Get user's position details
const [deposits, collateral, debt] = await vault.get_user_position(userAddress);

// Calculate user's equity
const totalAssets = await vault.total_assets();
const totalSupply = await vault.total_supply();
const userEquity = (shares * totalAssets) / totalSupply;
```

## API Integration

### Vesu Pool API

Get real-time pool statistics:

```typescript
const POOL_ID = "0x03976cac265a12609934089004df458ea29c776d77da423c96dc761d09d24124";

const response = await fetch(
    `https://api.vesu.xyz/pools/${POOL_ID}?onlyEnabledAssets=true`
);
const data = await response.json();

// Extract USDC borrow rate
const usdc = data.data.assets.find(a => a.symbol === 'USDC');
const borrowApr = Number(usdc.stats.borrowApr.value) / 1e18 * 100;

// Extract wBTC/USDC pair info
const pair = data.data.pairs.find(p => 
    p.collateralAssetAddress.includes('wbtc') &&
    p.debtAssetAddress.includes('usdc')
);
const maxLTV = Number(pair.maxLTV.value) / 1e18;
```

### AVNU API

Get swap quotes:

```typescript
const quote = await fetch('https://starknet.api.avnu.fi/swap/v2/quotes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        sellTokenAddress: CONTRACTS.USDC,
        buyTokenAddress: CONTRACTS.WBTC,
        sellAmount: '1000000',  // $1 USDC
        takerAddress: CONTRACTS.EXECUTOR,
    })
}).then(r => r.json());

console.log('Expected BTC out:', quote.buyAmount);
console.log('Price impact:', quote.priceImpact);
```

## Events

### Deposit Event

```cairo
struct DepositEvent {
    sender: ContractAddress,
    owner: ContractAddress,
    assets: u256,
    shares: u256,
}
```

### Withdraw Event

```cairo
struct WithdrawEvent {
    sender: ContractAddress,
    receiver: ContractAddress,
    owner: ContractAddress,
    assets: u256,
    shares: u256,
}
```

## Error Codes

| Error | Meaning |
|-------|---------|
| `ZERO_AMOUNT` | Cannot deposit or withdraw zero |
| `PAUSED` | Vault is paused |
| `INSUFFICIENT_SHARES` | User doesn't have enough shares |
| `SLIPPAGE` | Swap returned less than minimum |
| `ONLY_VAULT` | Only vault can trigger executor |
| `ONLY_VESU` | Only Vesu can call flash loan callback |

## Testing

### Local Development

```bash
# Clone repo
git clone https://github.com/unboundlabs/unbound
cd unbound

# Build contracts
cd contracts/v1
scarb build

# Run tests
snforge test
```

### Forked Testing

```bash
# Fork mainnet for testing
snforge test --fork-url https://starknet-mainnet.g.alchemy.com/...
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests
4. Submit PR

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
