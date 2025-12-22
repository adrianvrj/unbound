# Frequently Asked Questions

## General

### What is Unbound?

Unbound is an automated leveraged vault that allows you to gain amplified exposure to Bitcoin (wBTC) on Starknet. It uses Vesu V2 flash loans to achieve leverage in a single transaction.

### How does leverage work?

When you deposit wBTC with 2x leverage:
1. You deposit 1 wBTC
2. Unbound borrows 1 wBTC worth of USDC via flash loan
3. Swaps USDC to wBTC
4. Deposits all ~2 wBTC as collateral
5. Borrows USDC to repay flash loan

You now have 2x exposure to BTC price movements.

### What are vault shares (uBTC)?

When you deposit, you receive vault shares (token symbol: uBTC) representing your proportional ownership of the vault. When you withdraw, you burn shares to receive your portion of the vault's assets.

### Is Unbound custodial?

No. Unbound never holds your funds. All assets are deposited directly into Vesu lending pools. The Unbound contracts only coordinate the leverage operations.

---

## Deposits & Withdrawals

### What's the minimum deposit?

There's no minimum enforced by the contract, but very small deposits may not be economical due to gas costs.

### Can I deposit multiple times?

Yes. Each deposit mints additional shares proportional to your contribution.

### Can I partially withdraw?

Currently, `withdraw_all` withdraws your entire position. Partial withdrawals require redeeming a portion of your shares via ERC-4626 `redeem` function.

### How long does withdrawal take?

Withdrawal is instant—it happens in a single transaction. There's no waiting period or queue.

### Why might a withdrawal fail?

- **Insufficient liquidity**: During high volatility, DEX liquidity may be thin
- **High slippage**: If price moves more than your slippage tolerance
- **Contract paused**: If the vault is paused for emergency

---

## Leverage & Risk

### What leverage can I use?

The UI supports 1x to 4x leverage. Higher leverage = higher risk = higher potential gains/losses.

### What is the Health Factor?

Health Factor measures how safe your position is from liquidation:
- Health Factor > 1.0: Safe
- Health Factor < 1.0: Can be liquidated

```
Health Factor = (Collateral Value × 0.9) / Debt Value
```

### What is the Liquidation Price?

The price at which wBTC must fall for your position to be liquidatable:

```
Liquidation Price = Total Debt / (Total Collateral × 0.9)
```

### Can I get liquidated?

Yes, if BTC price falls enough that your Health Factor drops below 1.0. At that point, liquidators can repay your debt and claim your collateral.

### What happens if I get liquidated?

- Liquidators repay a portion of your debt
- They receive equivalent collateral + bonus (~10%)
- Your remaining position (if any) stays in the vault
- You may lose most or all of your deposit

### How do I avoid liquidation?

- Use lower leverage (2x is safer than 4x)
- Monitor your Health Factor
- Be ready to add collateral or withdraw if BTC drops significantly

---

## Fees & Costs

### What fees does Unbound charge?

**Performance Fee**: 1.5% of profits only
- Only charged when you withdraw at a profit
- No fee if you withdraw at a loss

**No other fees** from Unbound itself.

### What about borrowing costs?

You pay interest on borrowed USDC to Vesu:
- Base Borrow APR: ~1.8% (variable)
- BTCFi Rewards: ~1.4% (offset)
- **Net Cost**: ~0.4% annualized

### Are there gas fees?

Yes, standard Starknet transaction fees apply for:
- Deposit transactions
- Withdrawal transactions

Flash loans on Vesu are fee-free.

---

## Technical

### What blockchain is Unbound on?

Starknet mainnet—a Layer 2 scaling solution for Ethereum.

### Are the contracts audited?

Audits are in progress. The contracts follow standard ERC-4626 patterns and use OpenZeppelin Cairo libraries.

### Are the contracts upgradeable?

No. The current contracts are immutable. Any upgrades require deploying new contracts and users migrating their positions.

### Can the team access my funds?

No. The contracts are non-custodial. The owner can only:
- Pause deposits (not withdrawals)
- Change the performance fee (max 5%)
- Update the treasury address

### What happens if Unbound stops operating?

Your funds are in Vesu, not Unbound. You can always:
1. Withdraw via the Unbound contract
2. Or interact directly with Vesu if needed

---

## Tokens

### What is wBTC?

Wrapped Bitcoin—an ERC-20 token backed 1:1 by BTC. Address: `0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac`

### What are uBTC tokens?

Vault shares representing your position. 8 decimals (same as wBTC).

### Can I transfer vault shares?

Yes, uBTC is a standard ERC-20 token. You can transfer, hold in any wallet, or potentially use in other DeFi protocols.

---

## Troubleshooting

### My transaction failed. What do I do?

1. Check the error message in your wallet
2. Verify you have enough wBTC for the deposit
3. Ensure slippage isn't too tight
4. Try again with fresh AVNU calldata (prices change)

### I can't find my shares in my wallet.

Add the token manually:
- Contract: `0x03ca2746d882bfc63213dc264af5e0856e91c393f07c966607cc1492cec55aa9`
- Symbol: uBTC
- Decimals: 8

### My position value seems wrong.

Remember that shares represent proportional ownership. The value depends on:
- Total vault collateral
- Total vault debt
- Current BTC price

Check `get_vault_position()` for current state.
