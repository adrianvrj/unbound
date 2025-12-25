// Deposit Queue Module for UnboundVault V2
//
// Handles the queuing of deposits before they are processed by the backend
// and shares are minted to users.

use starknet::ContractAddress;

/// Deposit request structure
#[derive(Drop, Serde, starknet::Store, Copy)]
pub struct DepositRequest {
    pub user: ContractAddress,
    pub receiver: ContractAddress,
    pub wbtc_amount: u256,
    pub usdc_received: u256,
    pub min_shares: u256,
    pub timestamp: u64,
    pub processed: bool,
}

/// Deposit queue trait
#[starknet::interface]
pub trait IDepositQueue<TContractState> {
    /// Get the number of pending deposits
    fn pending_deposit_count(self: @TContractState) -> u256;

    /// Get a specific deposit request
    fn get_deposit_request(self: @TContractState, request_id: u256) -> DepositRequest;

    /// Get the next deposit to process
    fn get_next_pending_deposit(self: @TContractState) -> (u256, DepositRequest);
}
