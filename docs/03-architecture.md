# Architecture

This document describes the technical architecture of Unbound.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         UNBOUND SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│   │   Frontend   │      │   Backend    │      │    Vault     │ │
│   │   (Next.js)  │─────▶│   (FastAPI)  │◀────▶│  (Cairo)     │ │
│   └──────────────┘      └──────────────┘      └──────────────┘ │
│         │                      │                      │         │
│         │                      │                      │         │
│         ▼                      ▼                      ▼         │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│   │   Starknet   │      │   Extended   │      │    AVNU      │ │
│   │   Wallet     │      │   Exchange   │      │   Router     │ │
│   └──────────────┘      └──────────────┘      └──────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Smart Contracts

### Vault Contract (`vault.cairo`)

The vault is an ERC-4626 tokenized vault that:
- Accepts wBTC deposits
- Swaps to USDC via AVNU
- Mints shares proportional to deposit
- Handles withdrawals with USDC → wBTC swap

**Key Functions:**
```cairo
fn deposit(amount: u256, avnu_calldata: Array<felt252>) -> u256
fn withdraw(shares: u256, receiver: ContractAddress, owner: ContractAddress, avnu_calldata: Array<felt252>) -> u256
fn total_assets() -> u256
fn balance_of(owner: ContractAddress) -> u256
```

## Backend System

### FastAPI Server (`api.py`)

REST API for vault operations:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vault/status` | GET | Vault stats and APY |
| `/api/strategy/status` | GET | Strategy state |
| `/api/strategy/execute` | POST | Run strategy iteration |
| `/api/withdrawal/request` | POST | Request withdrawal |
| `/api/wallet/status` | GET | Operator wallet balance |

### Strategy Engine (`strategy.py`)

Implements funding rate arbitrage:
- Monitors funding rate from Extended API
- Opens SHORT when funding > threshold
- Closes position when funding < threshold
- Auto-executes after deposits

### Starknet Client (`starknet_client.py`)

Handles on-chain operations:
- Monitors operator wallet for USDC
- Deposits USDC to Extended
- Forwards USDC to vault for withdrawals

### Extended Client (`extended_client.py`)

Interacts with Extended exchange:
- Gets market data and funding rates
- Places orders using x10 SDK
- Manages positions and withdrawals

## External Integrations

### Extended Exchange

Perpetual futures exchange on Starknet:
- Deposit contract: `0x062da0780fae50d68cecaa5a051606dc21217ba290969b302db4dd99d2e9b470`
- Trading via REST API + Stark signatures
- Funding payments every hour

### AVNU Router

DEX aggregator for best swap rates:
- Address: `0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f`
- Used for wBTC ↔ USDC swaps

## Data Flow

### Deposit
```
User wBTC → Vault → AVNU → USDC → Operator → Extended → SHORT position
```

### Yield Generation
```
Extended → Funding payments every hour → Equity grows
```

### Withdrawal
```
Extended → USDC → Operator → Vault → AVNU → wBTC → User
```

## Security Model

| Component | Trust Assumption |
|-----------|------------------|
| Vault Contract | Trustless (on-chain) |
| Backend | Trust operator to run strategy honestly |
| Extended | Trust exchange custody |
| Operator Wallet | Controlled by backend |
