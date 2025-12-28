# Overview

## What is Unbound?

Unbound is a **Delta-Neutral BTC Yield Vault** that generates yield by capturing funding rate payments on perpetual futures exchanges. Users deposit wBTC and earn passive income without directional exposure to BTC price.

## The Opportunity

On perpetual futures exchanges, traders pay or receive **funding rates** every hour to keep the perpetual price aligned with spot:

| Market Condition | Funding Rate | Who Pays |
|------------------|--------------|----------|
| Bullish (more longs) | **Positive** | Longs pay Shorts |
| Bearish (more shorts) | **Negative** | Shorts pay Longs |

Historically, funding rates are positive ~84% of the time because traders are generally bullish on BTC.

## The Delta-Neutral Strategy

Unbound captures this yield through a hedged strategy:

1. **Keep 50% as wBTC** in the vault (LONG exposure)
2. **Swap 50% to USDC** and deposit to Extended exchange
3. **Open SHORT position** equal to wBTC value held (matches the hedge)
4. **Collect funding** when rate is positive (shorts receive payments)
5. **Close position** when funding turns negative (avoid paying)

### Why It's Delta-Neutral

```
Portfolio Breakdown:
├── 50% wBTC in vault    = +0.5 BTC exposure (LONG)
├── 50% USDC in Extended = $0 BTC exposure (margin for short)
└── SHORT position       = -0.5 BTC exposure
                          ─────────────────
                     Net = 0 BTC exposure (NEUTRAL)
```

BTC price movements are hedged: if BTC goes up, the wBTC gains offset the short losses. If BTC goes down, the short gains offset the wBTC losses.

## How Funding Payments Work

Extended uses this formula:
```
Funding Payment = Position Size × Mark Price × Funding Rate
```

- **If funding > 0**: Your SHORT receives payment from longs
- **If funding < 0**: Your SHORT pays to longs

Example with $5,000 deposit:
- wBTC kept in vault: $2,500 (LONG)
- USDC to Extended: $2,500 → opens $2,500 SHORT (matches wBTC value)
- Position size: ~0.0284 BTC (at $88,000)
- Funding rate: 0.0013%/hr
- **Hourly payment: ~$0.032**
- **Daily payment: ~$0.78**
- **Annual payment: ~$285** (~5-6% APY on total deposit)

## How It Benefits Users

| Benefit | Description |
|---------|-------------|
| **Passive Income** | ~5-12% APY depending on market conditions |
| **No Price Risk** | Delta-neutral means no exposure to BTC volatility |
| **Automated** | Strategy runs 24/7 without user intervention |
| **Tokenized** | Vault shares (uBTC) are ERC-20 tokens |

## Typical APY Range

| Market Condition | Funding Rate | APY on Total Deposit |
|------------------|--------------|----------------------|
| Low demand | 0.001%/hr | ~4% |
| Normal | 0.0015%/hr | ~6% |
| High demand | 0.003%/hr | ~12% |

*Funding rates vary based on market sentiment. Current rate may be higher or lower.*

## What Unbound Does NOT Do

- ❌ Guarantee profits (funding can be negative)
- ❌ Provide insurance against exchange risk
- ❌ Allow individual position management
