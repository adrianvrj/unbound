# FAQ

Frequently asked questions about Unbound.

## General Questions

### What is Unbound?

Unbound is a **BTC Funding Rate Arbitrage Vault** that earns yield by capturing funding payments on perpetual futures. Users deposit wBTC and earn passive income without directional exposure to BTC price.

### How does it generate yield?

On perpetual futures exchanges, traders pay **funding rates** every hour. When funding is positive (which happens ~70% of the time), long traders pay short traders. Unbound opens short positions to receive these payments.

### Is this delta-neutral?

Yes. The vault holds USDC as collateral and opens SHORT positions. Since USDC doesn't change with BTC price, and the short position's PnL is offset by funding payments over time, the strategy is market-neutral.

### What's the expected APY?

APY varies based on market sentiment:
- Bull markets (high funding): 40-100%+ APY
- Neutral markets: 15-30% APY
- Bear markets (low/negative funding): 0-10% APY

Historical average is approximately 20-60% APY.

## Deposits & Withdrawals

### What token do I deposit?

You deposit **wBTC** (wrapped Bitcoin on Starknet). The vault automatically converts it to USDC for the strategy.

### How long do deposits take?

Deposits are processed within minutes:
1. Vault receives your wBTC (~instant)
2. Swap to USDC (~30 seconds)
3. Deposit to Extended (~1-2 minutes)
4. Strategy executes (~immediate)

### How long do withdrawals take?

Withdrawals can take 5-15 minutes:
1. Request withdrawal through frontend
2. Backend closes any open positions
3. Extended processes withdrawal request
4. USDC is forwarded to vault
5. Vault swaps to wBTC and sends to you

### What token do I receive when withdrawing?

You receive **wBTC**, the same token you deposited.

## Strategy Questions

### What exchange does Unbound use?

Unbound uses **Extended Exchange**, a perpetual futures platform on Starknet that uses validity proofs for security.

### What leverage does the strategy use?

The default is **2x leverage**, which is conservative. This means liquidation would only occur if BTC rises 50%+ while in a short position.

### Can I lose money?

Yes, there are scenarios where returns could be negative:
- Extended periods of negative funding
- Exchange issues or hacks
- Extreme market movements causing liquidation

See the [Risk & Security](./05-risk-security.md) page for details.

### What are the fees?

- **Swap fees**: ~0.3% on deposit/withdrawal (AVNU)
- **Trading fees**: ~0.05% (Extended)
- **Performance fee**: TBD

## Technical Questions

### Are my funds custodied?

No. Your vault shares are yours on-chain. However, the USDC collateral is held on Extended exchange for trading. There is custody risk with the exchange.

### Can I see my position on Extended?

If you connect the operator wallet to Extended's UI, you can see the collective position. Individual user positions are tracked via vault shares.

### Is the code open source?

Yes. All smart contracts and backend code are open source on GitHub.

### What happens if the backend goes down?

Your funds remain safe in Extended. The strategy simply stops executing. The team can manually recover funds if needed.

## Troubleshooting

### My deposit is stuck

1. Check Voyager for transaction status
2. Verify backend is running
3. Contact support if issue persists

### I can't withdraw

1. Ensure you have shares (check "Your Position" page)
2. Wait for backend to process if recently requested
3. Try again after a few minutes

### The APY seems wrong

APY is estimated based on current funding rate and is variable. Check the strategy status for current funding rate.
