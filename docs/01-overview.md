# Overview

## What is Unbound?

Unbound is a **BTC Funding Rate Arbitrage Vault** that generates yield by capturing funding rate payments on perpetual futures exchanges. Users deposit wBTC and earn passive income without directional exposure to BTC price.

## The Opportunity

On perpetual futures exchanges, traders pay or receive **funding rates** every hour to keep the perpetual price aligned with spot:

| Market Condition | Funding Rate | Who Pays |
|------------------|--------------|----------|
| Bullish (more longs) | **Positive** | Longs pay Shorts |
| Bearish (more shorts) | **Negative** | Shorts pay Longs |

Historically, funding rates are positive ~70% of the time because traders are generally bullish on BTC.

## The Strategy

Unbound captures this yield through a simple strategy:

1. **Hold USDC as collateral** on Extended exchange
2. **Open SHORT position** when funding is positive (receive payments)
3. **Close position** when funding turns negative (avoid paying)
4. **Repeat** automatically

### Why It's Delta-Neutral

The USDC collateral doesn't change with BTC price. Small unrealized PnL from the short position is offset by the funding payments received. Net result: **stable yield regardless of BTC direction**.

## How It Benefits Users

| Benefit | Description |
|---------|-------------|
| **Passive Income** | ~20-60% APY depending on market conditions |
| **No Price Risk** | Delta-neutral means no exposure to BTC volatility |
| **Automated** | Strategy runs 24/7 without user intervention |
| **Tokenized** | Vault shares (uBTC) are ERC-20 tokens |

## Example Returns

| Funding Rate | APY (with 2x leverage) |
|--------------|------------------------|
| 0.001% / hour | ~17% |
| 0.005% / hour | ~87% |
| 0.01% / hour | ~175% |

*Funding rates vary based on market sentiment.*

## What Unbound Does NOT Do

- ❌ Guarantee profits (funding can be negative)
- ❌ Provide insurance against exchange risk
- ❌ Allow individual position management
