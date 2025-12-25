# Risk & Security

This document outlines the risks and security considerations of using Unbound.

## Risk Categories

### 1. Strategy Risk

**Negative Funding Periods**
- Risk: Funding rates can turn negative (~16% of time)
- Mitigation: PositionManager closes positions when funding < -0.01%
- Impact: Reduced yield during negative periods, but no losses from payments

**Delta Drift**
- Risk: Imbalance between wBTC value and short position
- Mitigation: Automatic rebalancing when delta > 5%
- Impact: Brief periods of directional exposure

### 2. Exchange Risk

**Extended Exchange Custody**
- Risk: USDC collateral is held on Extended exchange
- Impact: If Extended is hacked/insolvent, USDC portion at risk
- Mitigation: Extended uses Starknet validity proofs

**Note:** 50% of deposits remain as wBTC in the vault contract, reducing exchange exposure.

### 3. Smart Contract Risk

**Vault Contract Bugs**
- Risk: Bugs could lock or lose funds
- Mitigation: Simple ERC-4626 design, open source code

**Swap Slippage**
- Risk: Poor rates during wBTC ↔ USDC swaps
- Mitigation: Slippage protection + AVNU best routing

### 4. Operator Risk

**Backend Downtime**
- Risk: Backend services go offline
- Impact: No new deposits processed, no rebalancing
- Mitigation: Funds remain safe; manual recovery possible

**Operator Key Compromise**
- Risk: Private key stolen
- Impact: Attacker could withdraw from Extended
- Mitigation: Secure key storage, monitoring

## Position Risks

### Price Movement (Hedged)

The delta-neutral design hedges price risk:

| BTC Move | wBTC in Vault | Short PnL | Net Position |
|----------|---------------|-----------|--------------|
| +10% | +$10 | -$10 | ~$0 |
| -10% | -$10 | +$10 | ~$0 |

**Result:** Price movements are offset by the hedge.

### Liquidation Risk

With 2x leverage on USDC portion:
- Liquidation occurs if BTC rises ~50% without rebalancing
- PositionManager monitors margin ratio
- Conservative leverage minimizes this risk

## Security Measures

| Measure | Implementation |
|---------|----------------|
| Key Security | Environment variables, not in code |
| Queue System | On-chain deposit/withdrawal queues |
| Access Control | Operator-only functions for processing |
| Signature Verification | NAV updates require operator signature |

## Best Practices for Users

1. **Start Small**: Test with small amounts first
2. **Understand Risks**: Funding can be negative, exchange has custody
3. **Monitor**: Check position status regularly
4. **Diversify**: Don't put all funds in one vault

## Emergency Procedures

### If Backend Goes Down
1. Funds remain in Extended + vault
2. Owner can manually recover using operator wallet
3. wBTC in vault is always accessible

### Full Recovery
1. Close all positions on Extended
2. Withdraw USDC to operator wallet
3. Forward USDC to vault contract
4. Users withdraw their proportional share
