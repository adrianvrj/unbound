# FAQ

Frequently asked questions about Unbound.

## General Questions

### What is Unbound?

Unbound is a **Delta-Neutral BTC Yield Vault** that earns yield by capturing funding payments on perpetual futures. Users deposit wBTC and earn passive income without directional exposure to BTC price.

### How does it generate yield?

On perpetual futures exchanges, traders pay **funding rates** every hour. When funding is positive (~84% of the time), long traders pay short traders. Unbound opens short positions to receive these payments.

### Is this delta-neutral?

Yes. The vault uses a 50/50 strategy:
- **50% kept as wBTC** in the vault (LONG exposure)
- **50% converted to USDC** → deposited to Extended → opens SHORT

The short position matches the wBTC value, creating a market-neutral position with net 0 BTC exposure.

### What's the expected APY?

APY depends on current funding rates:

| Market Condition | Funding Rate | APY |
|------------------|--------------|-----|
| Low demand | 0.001%/hr | ~4% |
| Normal | 0.0015%/hr | ~6% |
| High demand | 0.003%/hr | ~12% |

*APY varies with market conditions. Only 50% of your deposit generates yield (the short position).*

## Deposits & Withdrawals

### What token do I deposit?

You deposit **wBTC** (wrapped Bitcoin on Starknet).

### What happens to my deposit?

1. 50% is kept as wBTC in the vault
2. 50% is swapped to USDC and deposited to Extended
3. A SHORT position is opened to hedge the wBTC

### How long do deposits take?

Processing takes ~2-5 minutes:
1. Vault receives wBTC (~instant)
2. Swap to USDC (~30 seconds)
3. Backend deposits to Extended (~1-2 minutes)
4. SHORT position opens (~30 seconds)

### How long do withdrawals take?

Withdrawals can take 5-15 minutes:
1. Request withdrawal (instant)
2. Backend closes proportional position
3. USDC withdrawn from Extended
4. Vault swaps USDC → wBTC
5. You receive wBTC

### What token do I receive?

You receive **wBTC**, same as you deposited.

### Is there a minimum deposit?

Yes, **0.00025 wBTC** (~$25 USD) to ensure the SHORT position meets Extended's minimum trade size.

## Strategy Questions

### What exchange does Unbound use?

**Extended Exchange** - a perpetual futures platform on Starknet with validity proofs.

### What leverage is used?

The account uses **2x leverage** which affects margin requirements but **not APY**. 

- Short position size = wBTC value (50% of deposit)
- Leverage allows using ~50% of margin for the position
- The remaining margin acts as a safety buffer against liquidation

**Important**: Higher leverage does not increase yield. Only the position size determines funding payments.

### Can I lose money?

Yes, scenarios where returns could be negative:
- Extended periods of negative funding
- Exchange issues or hacks
- Extreme price moves before rebalancing

See [Risk & Security](./05-risk-security.md) for details.

### What are the fees?

- **Swap fees**: ~0.3% on deposit/withdrawal (AVNU)
- **Trading fees**: ~0.05% (Extended)
- **Performance fee**: TBD

## Technical Questions

### Are my funds custodied?

Partially:
- **wBTC in vault**: On-chain, under contract control
- **USDC on Extended**: Exchange custody (risk)

### How does funding work?

Extended calculates funding every hour:
```
Funding Payment = Position Size × Mark Price × Funding Rate
```

If rate is positive, your SHORT receives payment.

### What if funding goes negative?

The `PositionManager` monitors funding rate. If it drops below -0.01%, it closes positions to avoid paying. Positions reopen when funding recovers.

### Is the code open source?

Yes. All contracts and backend code on GitHub.

## Troubleshooting

### My deposit is stuck

1. Check transaction on Voyager
2. Deposits are processed every 30 seconds
3. Contact support if >10 minutes

### I can't withdraw

1. Ensure you have shares (check "Your Position")
2. Withdrawals process every 30 seconds
3. Wait for "Ready" status, then click "Complete"

### The APY seems wrong

APY shown is based on current funding rate. The 30-day average is shown in the tooltip. Actual returns depend on funding during your holding period.
