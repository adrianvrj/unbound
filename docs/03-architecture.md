# Architecture

## Overview

Unbound consists of two main smart contracts that work together to provide leveraged vault functionality:

```
┌─────────────────────────────────────────────────────────────────┐
│                         UNBOUND SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────┐          ┌───────────────────────────┐     │
│   │    Vault      │─────────→│       Executor            │     │
│   │  (ERC-4626)   │          │  (Flash Loan Receiver)    │     │
│   └───────────────┘          └───────────────────────────┘     │
│         │                              │                        │
│         │                              │                        │
│         ▼                              ▼                        │
│   ┌─────────────────────────────────────────────────┐          │
│   │                   VESU V2 POOL                   │          │
│   │  • Flash Loans  • Positions  • Collateral/Debt  │          │
│   └─────────────────────────────────────────────────┘          │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────┐          │
│   │                   AVNU ROUTER                    │          │
│   │              • DEX Aggregator                    │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Contract Details

### UnboundVault

**Purpose**: User-facing contract for deposits and withdrawals. Implements ERC-4626 tokenized vault standard.

**Key Responsibilities**:
- Accept user deposits
- Mint/burn vault shares
- Track user positions
- Coordinate with Executor for leverage operations
- Collect performance fees

**Storage**:
```cairo
struct Storage {
    underlying_asset: ContractAddress,  // wBTC
    debt_asset: ContractAddress,        // USDC
    vesu_pool: ContractAddress,
    executor: ContractAddress,
    paused: bool,
    performance_fee_bps: u256,
    treasury: ContractAddress,
}
```

### FlashLoanExecutor

**Purpose**: Handles the flash loan callback and executes the leverage/deleverage operations.

**Key Responsibilities**:
- Receive flash loans from Vesu
- Execute swaps via AVNU
- Manage Vesu position (deposit collateral, borrow debt)
- Ensure atomicity of operations

**Security**: Only the Vesu Pool can call `on_flash_loan`.

```cairo
fn on_flash_loan(
    sender: ContractAddress,  // Must be Vault
    asset: ContractAddress,   // USDC
    amount: u256,
    data: Span<felt252>       // Operation details
)
```

## External Integrations

### Vesu V2

[Vesu](https://vesu.xyz) is Starknet's lending protocol used for:

| Function | Usage |
|----------|-------|
| `flash_loan` | Get USDC without collateral |
| `modify_position` | Add collateral / borrow debt |
| `position` | Query current position state |
| `price` | Get asset oracle prices |

**Pool Parameters** (wBTC/USDC pair):
- Max LTV: 86%
- Liquidation Factor: 90%
- Borrow APR: Variable (~1.8%)
- BTCFi Rewards: ~1.4% (reduces net cost)

### AVNU

[AVNU](https://avnu.fi) is a DEX aggregator for optimal swap execution:

| Function | Usage |
|----------|-------|
| `multi_route_swap` | Execute USDC ↔ wBTC swaps |

**Why AVNU?**
- Best execution across multiple DEXs
- Single transaction for complex routes
- Built-in slippage protection

## Data Flow

### Position Creation

```
1. User → Vault: deposit_and_leverage(wBTC, flashAmount, ...)
2. User → Vault: wBTC transfer
3. Vault → Vesu: flash_loan(USDC)
4. Vesu → Executor: on_flash_loan(USDC)
5. Executor → AVNU: swap(USDC → wBTC)
6. Executor → Vesu: modify_position(deposit wBTC)
7. Executor → Vesu: modify_position(borrow USDC)
8. Executor → Vesu: repay flash loan
9. Vault → User: mint shares
```

### Position Closure

```
1. User → Vault: withdraw_all(...)
2. Vault: burn shares
3. Vault → Vesu: flash_loan(USDC)
4. Vesu → Executor: on_flash_loan(USDC)
5. Executor → Vesu: modify_position(repay debt)
6. Executor → Vesu: modify_position(withdraw wBTC)
7. Executor → AVNU: swap(wBTC → USDC) [partial]
8. Executor → Vesu: repay flash loan
9. Vault → User: transfer remaining wBTC
```

## Trust Model

| Entity | Trust Level | Why |
|--------|-------------|-----|
| Vault Owner | High | Can pause, set fees |
| Executor | Medium | Only vault can trigger operations |
| Vesu | Critical | Holds all collateral and debt |
| AVNU | Medium | Swap execution only |
| User | None needed | Permission-less interaction |

## Upgrade Path

Current contracts are **not upgradeable**. To upgrade:
1. Deploy new vault with updated logic
2. Users withdraw from old vault
3. Users deposit to new vault

This ensures users always have full control over their assets.
