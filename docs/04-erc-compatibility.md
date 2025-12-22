# ERC Compatibility

Unbound implements standard token interfaces to ensure compatibility with wallets, explorers, and DeFi protocols.

## ERC-4626: Tokenized Vault Standard

The Unbound Vault implements **ERC-4626**, the standard for tokenized vaults. This enables:

- Compatibility with vault aggregators
- Standard deposit/withdraw interfaces
- Predictable share calculation

### Implemented Functions

| Function | Description | Status |
|----------|-------------|--------|
| `asset()` | Returns underlying asset (wBTC) | ✅ |
| `totalAssets()` | Returns total vault assets | ✅ |
| `convertToShares(assets)` | Preview shares for deposit | ✅ |
| `convertToAssets(shares)` | Preview assets for redeem | ✅ |
| `maxDeposit(receiver)` | Maximum deposit allowed | ✅ |
| `previewDeposit(assets)` | Preview deposit result | ✅ |
| `deposit(assets, receiver)` | Deposit and mint shares | ✅ |
| `maxWithdraw(owner)` | Maximum withdraw allowed | ✅ |
| `previewWithdraw(assets)` | Preview withdraw result | ✅ |
| `withdraw(assets, receiver, owner)` | Withdraw assets | ✅ |
| `maxRedeem(owner)` | Maximum redeem allowed | ✅ |
| `previewRedeem(shares)` | Preview redeem result | ✅ |
| `redeem(shares, receiver, owner)` | Redeem shares for assets | ✅ |

### Custom Extensions

Beyond ERC-4626, Unbound adds:

```cairo
// Leverage-specific deposit
fn deposit_and_leverage(
    assets: u256,
    flash_loan_amount: u256,
    min_collateral_out: u256,
    avnu_calldata: Array<felt252>
) -> u256

// Full position withdrawal
fn withdraw_all(
    min_underlying_out: u256,
    avnu_calldata: Array<felt252>
) -> u256

// Position info
fn get_vault_position() -> (u256, u256)
fn get_user_position(user: ContractAddress) -> (u256, u256, u256)
```

## ERC-20: Token Standard

The vault shares (uBTC) are fully ERC-20 compliant:

### Token Details

| Property | Value |
|----------|-------|
| Name | `Unbound wBTC Vault` |
| Symbol | `uBTC` |
| Decimals | `8` (matches wBTC) |

### Implemented Functions

| Function | Description |
|----------|-------------|
| `name()` | Token name |
| `symbol()` | Token symbol |
| `decimals()` | Token decimals (8) |
| `totalSupply()` | Total shares outstanding |
| `balanceOf(account)` | User's share balance |
| `transfer(to, amount)` | Transfer shares |
| `approve(spender, amount)` | Approve spending |
| `allowance(owner, spender)` | Check allowance |
| `transferFrom(from, to, amount)` | Transfer with approval |

### CamelCase Compatibility

For compatibility with both snake_case and camelCase conventions:

| snake_case | camelCase |
|------------|-----------|
| `total_supply` | `totalSupply` |
| `balance_of` | `balanceOf` |
| `transfer_from` | `transferFrom` |

## Share Calculation

### Deposit

```
shares = (assets * total_supply) / total_assets
```

For the first depositor (when total_supply = 0):
```
shares = assets  // 1:1 ratio
```

### Withdrawal

```
assets = (shares * total_assets) / total_supply
```

### Important Notes

1. **Decimals Match**: Vault shares have 8 decimals matching wBTC. This means 1 vault share represents approximately 1 satoshi of underlying value.

2. **Leveraged Assets**: `totalAssets()` returns the **total collateral** in Vesu, not the original deposits. This means the ratio of shares to assets changes based on leverage.

3. **Share Value**: Each share represents a proportional claim on:
   - Total collateral in Vesu
   - Minus total debt to Vesu
   - = Net vault equity

## Wallet Compatibility

Tested compatible with:

- ✅ Argent X
- ✅ Braavos
- ✅ Block explorers (Voyager, Starkscan)
- ✅ Token lists
