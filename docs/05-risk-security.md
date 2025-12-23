# Risk & Security

This document outlines the risks and security considerations of using Unbound.

## Risk Categories

### 1. Strategy Risk

**Negative Funding Periods**
- Risk: Funding rates can turn negative, meaning shorts pay longs
- Mitigation: Strategy closes positions when funding < threshold
- Impact: Reduced yield during negative funding periods

**Low Funding Periods**
- Risk: Funding rates near zero generate minimal yield
- Impact: Lower than expected returns

### 2. Exchange Risk

**Extended Exchange Custody**
- Risk: USDC is held on Extended exchange
- Impact: If Extended is hacked/insolvent, funds could be lost
- Mitigation: Extended uses Starknet validity proofs

**Exchange Downtime**
- Risk: Extended API/exchange unavailable
- Impact: Unable to execute strategy or withdraw
- Mitigation: Backend retries and manual fallbacks

### 3. Smart Contract Risk

**Vault Contract Bugs**
- Risk: Bugs in vault contract could lock funds
- Mitigation: Simple contract design, open source

**Swap Slippage**
- Risk: Poor swap rates during wBTC ↔ USDC conversion
- Mitigation: Slippage protection in contract + AVNU best routing

### 4. Operator Risk

**Backend Downtime**
- Risk: Backend service goes offline
- Impact: Strategy stops executing, no new deposits processed
- Mitigation: Funds remain safe in Extended, can be manually recovered

**Operator Key Compromise**
- Risk: Operator private key stolen
- Impact: Attacker could withdraw from Extended to operator wallet
- Mitigation: Key stored securely, monitoring for unusual activity

## Position Risks

### Unrealized PnL

Short positions have unrealized PnL:
- If BTC price rises: Unrealized loss on short
- If BTC price falls: Unrealized gain on short

**Example:**
| BTC Price Move | Short PnL | Funding Received | Net |
|----------------|-----------|------------------|-----|
| +5% | -$500 | +$100 (week) | -$400 |
| -5% | +$500 | +$100 (week) | +$600 |

The strategy is delta-neutral over time as funding payments offset price movements.

### Liquidation Risk

With 2x leverage:
- Liquidation at ~50% move against position
- Example: If BTC rises 50%+ rapidly, position could be liquidated

**Mitigation:**
- Conservative leverage (2x default)
- Positions closed when funding is unfavorable

## Security Measures

| Measure | Implementation |
|---------|----------------|
| Key Security | Operator key stored in environment variables |
| API Authentication | Extended API key with limited permissions |
| Transaction Signing | Stark signatures via x10 SDK |
| Access Control | Vault has Ownable pattern |

## Best Practices for Users

1. **Start Small**: Test with small amounts first
2. **Understand the Strategy**: Know that yield comes from funding rates
3. **Monitor**: Check your position regularly
4. **Diversify**: Don't put all funds in one vault

## Emergency Procedures

### If Backend Goes Down
- Funds remain in Extended
- Owner can manually withdraw using operator wallet
- Users can request admin assistance

### If Extended Has Issues
- Monitor Extended status
- Funds can be withdrawn when service resumes

### Full Recovery
1. Withdraw all funds from Extended manually
2. Send USDC to vault contract
3. Users withdraw their share via contract
