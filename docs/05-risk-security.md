# Risk & Security

This document outlines the risks associated with using Unbound and the security measures in place.

## ⚠️ Risk Warning

**Leveraged positions are high-risk.** You can lose more than your initial deposit. Only use funds you can afford to lose.

## Position Risks

### 1. Liquidation Risk

If the value of your collateral falls below the required threshold, your position will be liquidated.

**How liquidation works:**
1. Collateral value drops relative to debt
2. Health Factor falls below 1.0
3. Liquidators repay debt and claim collateral + bonus
4. You lose your position

**Liquidation Parameters:**

| Parameter | Value |
|-----------|-------|
| Max LTV | 86% |
| Liquidation Factor | 90% |
| Liquidation Bonus | ~10% |

### Health Factor

```
Health Factor = (Collateral Value × Liquidation Factor) / Debt Value
```

| Health Factor | Risk Level | Action |
|---------------|------------|--------|
| > 2.0 | Safe | ✅ Position is healthy |
| 1.5 - 2.0 | Moderate | ⚠️ Monitor closely |
| 1.2 - 1.5 | High | 🔴 Consider reducing leverage |
| < 1.2 | Critical | 🚨 Liquidation imminent |
| < 1.0 | Liquidated | ❌ Position can be liquidated |

### Liquidation Price

```
Liquidation Price = Debt / (Collateral × Liquidation Factor)
```

**Example with 2x leverage:**
- Deposit: 1 wBTC @ $100,000
- Total Collateral: 2 wBTC
- Debt: $100,000 USDC
- Liquidation Price: $100,000 / (2 × 0.9) = **$55,555**

BTC would need to fall ~44% for liquidation.

### 2. Interest Rate Risk

Borrowing USDC incurs interest that accrues over time:

- **Base Borrow APR**: ~1.8% (variable)
- **BTCFi Rewards**: ~1.4% (reduces net cost)
- **Net Borrowing Cost**: ~0.4%

Interest rates can change based on:
- Pool utilization
- Market conditions
- Protocol governance

### 3. Smart Contract Risk

Unbound relies on multiple smart contracts:

| Contract | Risk |
|----------|------|
| Unbound Vault | Core logic bugs |
| Unbound Executor | Flash loan handling errors |
| Vesu Pool | Lending protocol vulnerabilities |
| AVNU Router | Swap execution failures |

### 4. Oracle Risk

Vesu uses oracles for price feeds. Oracle failures could cause:
- Incorrect liquidation triggers
- Wrong collateral valuations
- Trading halts

### 5. Liquidity Risk

During high volatility:
- DEX liquidity may dry up
- Swap slippage increases
- Withdrawals may receive less than expected

## Security Measures

### Smart Contract Security

| Measure | Status |
|---------|--------|
| Access Controls | ✅ Owner-only admin functions |
| Reentrancy Protection | ✅ Checks-effects-interactions |
| Flash Loan Validation | ✅ Only Vesu can call callback |
| Delegation Required | ✅ Executor needs vault delegation |
| Pause Functionality | ✅ Emergency pause available |

### Access Control

```cairo
// Only owner can:
fn set_performance_fee(...)  // Change fee (max 5%)
fn pause() / fn unpause()     // Emergency controls
fn set_treasury(...)          // Change fee recipient
```

### Flash Loan Security

```cairo
fn on_flash_loan(...) {
    // Only Vesu can call this
    assert(get_caller_address() == self.vesu_pool.read(), "only-vesu");
    
    // Only vault can trigger operations
    assert(sender == self.vault.read(), "only-vault");
}
```

### Slippage Protection

All swaps include `min_out` parameters:
- `min_collateral_out` for deposits
- `min_underlying_out` for withdrawals

If slippage exceeds tolerance, transaction reverts.

## Fees

### Performance Fee

- **Rate**: 1.5% (configurable, max 5%)
- **Applied to**: Profits only
- **Collected**: On withdrawal

```
fee = (withdrawal_value - deposit_value) × fee_rate
```

### Network Fees

Standard Starknet gas fees apply for:
- Deposit transactions
- Withdrawal transactions
- (Flash loans on Vesu are fee-free)

## Mitigation Strategies

### For Users

1. **Start Small**: Test with small amounts first
2. **Monitor Position**: Check health factor regularly
3. **Lower Leverage**: Use 2x instead of 4x for safety
4. **Set Alerts**: Use monitoring tools for price alerts
5. **Diversify**: Don't put all funds in one position

### For Protocol

1. **Audits**: Smart contract audits (in progress)
2. **Bug Bounty**: Immunefi program (planned)
3. **Gradual Rollout**: TVL caps during launch
4. **Monitoring**: On-chain monitoring for anomalies

## Emergency Procedures

### If Position is Near Liquidation

1. Add more collateral (deposit more wBTC)
2. Or partially close position to reduce debt
3. Or fully withdraw before liquidation

### If Protocol is Paused

- Withdrawals remain enabled
- New deposits are blocked
- Wait for unpause or governance action

### If Vesu is Compromised

- Unbound cannot protect against Vesu vulnerabilities
- Monitor Vesu announcements
- Consider withdrawing if concerns arise

## Disclaimer

This documentation is for informational purposes only. It does not constitute financial advice. Users are responsible for their own decisions and should conduct their own research. The Unbound team is not liable for losses incurred through use of the protocol.
