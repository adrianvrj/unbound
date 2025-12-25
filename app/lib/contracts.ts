// Contract addresses - MAINNET
export const CONTRACTS = {
    // Delta-Neutral Vault v6 (wBTC distribution fix - 2024-12-24)
    VAULT: "0x0291a1d4829bf8852aa5182409cc5b5f7c15a2709a5e5a5ff8e44791996acb62",

    // AVNU Router (Mainnet)
    AVNU_ROUTER: "0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f",

    // Tokens on Mainnet
    WBTC: "0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac",
    USDC: "0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8",
};

// ERC20 ABI for balance checks
export const ERC20_ABI = [
    {
        "type": "function",
        "name": "balance_of",
        "inputs": [
            {
                "name": "account",
                "type": "core::starknet::contract_address::ContractAddress"
            }
        ],
        "outputs": [
            {
                "type": "core::integer::u256"
            }
        ],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "approve",
        "inputs": [
            {
                "name": "spender",
                "type": "core::starknet::contract_address::ContractAddress"
            },
            {
                "name": "amount",
                "type": "core::integer::u256"
            }
        ],
        "outputs": [
            {
                "type": "core::bool"
            }
        ],
        "state_mutability": "external"
    }
];

// Vault ABI for the Funding Rate Vault (V1 + V2 compatible)
export const VAULT_ABI = [
    // ============ Deposit ============
    {
        "type": "function",
        "name": "deposit",
        "inputs": [
            { "name": "assets", "type": "core::integer::u256" },
            { "name": "receiver", "type": "core::starknet::contract_address::ContractAddress" },
            { "name": "min_shares", "type": "core::integer::u256" },
            { "name": "avnu_calldata", "type": "core::array::Array::<core::felt252>" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "external"
    },
    // ============ Withdrawal Queue (V2) ============
    {
        "type": "function",
        "name": "request_withdraw",
        "inputs": [
            { "name": "shares", "type": "core::integer::u256" },
            { "name": "min_assets", "type": "core::integer::u256" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "external"
    },
    {
        "type": "function",
        "name": "complete_withdraw",
        "inputs": [
            { "name": "request_id", "type": "core::integer::u256" },
            { "name": "avnu_calldata", "type": "core::array::Array::<core::felt252>" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "external"
    },
    {
        "type": "function",
        "name": "cancel_withdraw",
        "inputs": [
            { "name": "request_id", "type": "core::integer::u256" }
        ],
        "outputs": [],
        "state_mutability": "external"
    },
    {
        "type": "function",
        "name": "get_withdrawal_status",
        "inputs": [
            { "name": "request_id", "type": "core::integer::u256" }
        ],
        "outputs": [{ "type": "core::integer::u8" }],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "get_pending_withdrawal",
        "inputs": [
            { "name": "request_id", "type": "core::integer::u256" }
        ],
        "outputs": [
            { "type": "(core::starknet::contract_address::ContractAddress, core::integer::u256, core::integer::u256, core::integer::u256, core::integer::u64, core::integer::u8)" }
        ],
        "state_mutability": "view"
    },
    // ============ Legacy Withdraw (V1) ============
    {
        "type": "function",
        "name": "withdraw",
        "inputs": [
            { "name": "shares", "type": "core::integer::u256" },
            { "name": "receiver", "type": "core::starknet::contract_address::ContractAddress" },
            { "name": "owner", "type": "core::starknet::contract_address::ContractAddress" },
            { "name": "avnu_calldata", "type": "core::array::Array::<core::felt252>" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "external"
    },
    // ============ View Functions ============
    {
        "type": "function",
        "name": "balance_of",
        "inputs": [
            { "name": "account", "type": "core::starknet::contract_address::ContractAddress" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "total_assets",
        "inputs": [],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "preview_redeem",
        "inputs": [
            { "name": "shares", "type": "core::integer::u256" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "preview_deposit",
        "inputs": [
            { "name": "assets", "type": "core::integer::u256" }
        ],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "get_deposit_queue_length",
        "inputs": [],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "view"
    },
    {
        "type": "function",
        "name": "get_withdrawal_queue_length",
        "inputs": [],
        "outputs": [{ "type": "core::integer::u256" }],
        "state_mutability": "view"
    }
];