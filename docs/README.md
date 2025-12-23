# Unbound Documentation

Welcome to Unbound - a **BTC Funding Rate Arbitrage Vault** on Starknet.

## Quick Links

| Document | Description |
|----------|-------------|
| [Overview](./01-overview.md) | What is Unbound and how it generates yield |
| [How It Works](./02-how-it-works.md) | Complete flow of deposits and withdrawals |
| [Architecture](./03-architecture.md) | Smart contract and backend design |
| [Risk & Security](./05-risk-security.md) | Risks and security considerations |
| [For Developers](./06-for-developers.md) | API reference and contract addresses |
| [FAQ](./07-faq.md) | Frequently asked questions |

## What is Unbound?

Unbound is a **delta-neutral yield vault** that earns returns by capturing funding rate payments on perpetual futures. Users deposit wBTC and earn yield without directional exposure to BTC price movements.

### Key Features

- **Delta Neutral**: No exposure to BTC price movements
- **Passive Yield**: ~20-60% APY from funding rate payments
- **Non-Custodial**: Your shares represent ownership in the vault
- **Automated**: Strategy runs automatically 24/7

## Deployed Contracts (Mainnet)

| Contract | Address |
|----------|---------|
| Vault | `0x066db06cfe7d18c11f6ed5bf93dfb0db7e4ff40d8f5a41e9f7e2d01ebb7e16b8` |

## External Integrations

| Component | Description |
|-----------|-------------|
| Extended Exchange | Perpetual futures for funding rate arbitrage |
| AVNU Router | DEX aggregator for wBTC ↔ USDC swaps |
