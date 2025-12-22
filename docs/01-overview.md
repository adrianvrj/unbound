# Overview

## What is Unbound?

Unbound is an **automated leveraged vault** that allows users to amplify their Bitcoin exposure on Starknet. By abstracting away the complexity of "looping" (repeatedly depositing and borrowing), Unbound enables one-click leveraged positions.

## The Problem

Manually achieving leverage on lending protocols requires:

1. Deposit collateral (wBTC)
2. Borrow stablecoins (USDC)
3. Swap USDC → wBTC
4. Deposit the new wBTC as more collateral
5. Repeat until desired leverage is reached

This process is:
- **Time-consuming**: Multiple transactions required
- **Gas-intensive**: Each step costs transaction fees
- **Error-prone**: Easy to make mistakes during looping
- **Capital-inefficient**: Requires waiting between transactions

## The Unbound Solution

Unbound uses **flash loans** to achieve leverage in a single atomic transaction:

```
User deposits 1 wBTC → Flash loan USDC → Swap to wBTC → Deposit all as collateral → Borrow USDC → Repay flash loan
```

**Result**: 2.5x leverage achieved instantly.

## How It Benefits Users

| Benefit | Description |
|---------|-------------|
| **Simplicity** | One transaction instead of many |
| **Atomicity** | Either everything succeeds or everything reverts |
| **Gas Efficiency** | Single transaction = lower total fees |
| **No Slippage Risk** | Flash loan guarantees execution |

## Use Cases

### 1. Bullish on Bitcoin
You believe BTC will go up and want amplified exposure. With Unbound:
- Deposit 1 wBTC
- Select 2x leverage
- Now have exposure to 2 wBTC worth of price movement

### 2. Yield Farming with Leverage
Some protocols offer incentives (like Starknet BTCFi rewards) for borrowing. With leverage:
- Amplify your borrowing position
- Earn more rewards relative to your initial deposit

### 3. Hedged Positions
Combine leveraged long with other strategies to create sophisticated positions.

## Position Economics

When you open a leveraged position:

| Component | Example (2x on 1 wBTC @ $100k) |
|-----------|-------------------------------|
| Your Deposit | 1 wBTC ($100,000) |
| Borrowed USDC | $100,000 |
| Total Collateral | ~2 wBTC ($200,000) |
| Total Debt | $100,000 USDC |
| **Net Exposure** | 2x to BTC price |

### When BTC Goes Up 10%
- Collateral Value: 2.2 wBTC = $220,000
- Debt: $100,000
- Equity: $120,000 (**+20% gain**, 2x amplified)

### When BTC Goes Down 10%
- Collateral Value: 1.8 wBTC = $180,000
- Debt: $100,000
- Equity: $80,000 (**-20% loss**, 2x amplified)

## What Unbound Does NOT Do

- ❌ Custody your funds (all assets are in Vesu)
- ❌ Guarantee profits
- ❌ Protect against liquidation
- ❌ Provide insurance

See [Risk & Security](./05-risk-security.md) for more details on risks.
