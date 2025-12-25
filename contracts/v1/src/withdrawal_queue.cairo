// Withdrawal Queue Module for UnboundVault V2
//
// Handles the queuing of withdrawals with state machine:
// PENDING -> PROCESSING -> READY -> COMPLETED
// or PENDING -> CANCELLED

use starknet::ContractAddress;

/// Withdrawal status constants
pub mod Status {
    pub const PENDING: u8 = 0;
    pub const PROCESSING: u8 = 1;
    pub const READY: u8 = 2;
    pub const COMPLETED: u8 = 3;
    pub const CANCELLED: u8 = 4;
}

/// Withdrawal request structure
#[derive(Drop, Serde, starknet::Store, Copy)]
pub struct WithdrawalRequest {
    pub user: ContractAddress,
    pub shares: u256,
    pub min_assets: u256,
    pub usdc_value: u256, // Calculated when marked ready
    pub timestamp: u64,
    pub status: u8,
}

/// Withdrawal queue trait
#[starknet::interface]
pub trait IWithdrawalQueue<TContractState> {
    /// Get the number of pending withdrawals
    fn pending_withdrawal_count(self: @TContractState) -> u256;

    /// Get a specific withdrawal request
    fn get_withdrawal_request(self: @TContractState, request_id: u256) -> WithdrawalRequest;

    /// Get withdrawal status as string
    fn get_withdrawal_status_name(self: @TContractState, request_id: u256) -> felt252;

    /// Get all withdrawal request IDs for a user
    fn get_user_withdrawals(self: @TContractState, user: ContractAddress) -> Array<u256>;
}
