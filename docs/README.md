# Unbound Documentation

Welcome to the Unbound documentation. Unbound is an automated, non-custodial leveraged vault built on **Starknet** using **Vesu V2** lending protocol.

## Quick Links

| Document | Description |
|----------|-------------|
| [Overview](./01-overview.md) | What is Unbound and why it exists |
| [How It Works](./02-how-it-works.md) | Detailed flow of deposits, leverage, and withdrawals |
| [Architecture](./03-architecture.md) | Smart contract design and external integrations |
| [ERC Compatibility](./04-erc-compatibility.md) | ERC-4626 and ERC-20 compliance |
| [Risk & Security](./05-risk-security.md) | Liquidation risks, fees, and security considerations |
| [For Developers](./06-for-developers.md) | Integration guide, ABIs, and contract addresses |
| [FAQ](./07-faq.md) | Frequently asked questions |

## What is Unbound?

Unbound allows users to gain **leveraged exposure to Bitcoin** with a single transaction. Instead of manually looping deposits and borrows, Unbound automates the entire process using flash loans.

### Key Features

- **One-Click Leverage**: Deposit wBTC and get up to 4x exposure instantly
- **Non-Custodial**: Your assets remain in Vesu lending pools, not in our contracts
- **Tokenized Position**: Receive vault shares (ERC-20) representing your position
- **Automated Deleveraging**: Withdraw and unwind your position in one transaction

## Deployed Contracts (Mainnet)

| Contract | Address |
|----------|---------|
| Vault | `0x03ca2746d882bfc63213dc264af5e0856e91c393f07c966607cc1492cec55aa9` |
| Executor | `0x0208e65dcda65cf743a42132fa5c7587a67a49cf990155ab3646d13939ee8848` |

## External Dependencies

- **Vesu V2 Pool**: `0x0451fe483d5921a2919ddd81d0de6696669bccdacd859f72a4fba7656b97c3b5`
- **AVNU Router**: `0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f`
- **wBTC**: `0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac`
- **USDC**: `0x033068f6539f8e6e6b131e6b2b814e6c34a5224bc66947c47dab9dfee93b35fb`
