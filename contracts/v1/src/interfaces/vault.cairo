// Vault Interface for V2
use starknet::ContractAddress;

/// ERC-4626 Tokenized Vault Interface
#[starknet::interface]
pub trait IUnboundVaultV2<TContractState> {
    // ============ ERC-4626 View Functions ============

    /// Returns the address of the underlying asset (wBTC)
    fn asset(self: @TContractState) -> ContractAddress;

    /// Returns the total amount of underlying assets held by the vault
    fn total_assets(self: @TContractState) -> u256;

    /// Converts assets to shares
    fn convert_to_shares(self: @TContractState, assets: u256) -> u256;

    /// Converts shares to assets
    fn convert_to_assets(self: @TContractState, shares: u256) -> u256;

    /// Maximum deposit for receiver
    fn max_deposit(self: @TContractState, receiver: ContractAddress) -> u256;

    /// Preview deposit shares
    fn preview_deposit(self: @TContractState, assets: u256) -> u256;

    /// Maximum withdrawal for owner
    fn max_withdraw(self: @TContractState, owner: ContractAddress) -> u256;

    /// Preview withdrawal assets
    fn preview_withdraw(self: @TContractState, assets: u256) -> u256;

    /// Maximum redemption for owner
    fn max_redeem(self: @TContractState, owner: ContractAddress) -> u256;

    /// Preview redemption assets
    fn preview_redeem(self: @TContractState, shares: u256) -> u256;

    // ============ Deposit Functions ============

    /// Deposit wBTC and receive shares (queued)
    fn deposit(
        ref self: TContractState,
        assets: u256,
        receiver: ContractAddress,
        min_shares: u256,
        avnu_calldata: Array<felt252>,
    ) -> u256;

    // ============ Withdrawal Functions ============

    /// Request withdrawal (shares locked in queue)
    fn request_withdraw(
        ref self: TContractState, shares: u256, min_assets: u256,
    ) -> u256; // Returns request ID

    /// Complete withdrawal after processing
    fn complete_withdraw(
        ref self: TContractState, request_id: u256, avnu_calldata: Array<felt252>,
    ) -> u256;

    /// Cancel pending withdrawal
    fn cancel_withdraw(ref self: TContractState, request_id: u256);

    /// Get withdrawal request status
    fn get_withdrawal_status(self: @TContractState, request_id: u256) -> u8;

    // ============ Admin Functions ============

    fn pause(ref self: TContractState);
    fn unpause(ref self: TContractState);
    fn set_guardian(ref self: TContractState, guardian: ContractAddress);
    fn update_nav(
        ref self: TContractState, new_nav: u256, timestamp: u64, signature: Array<felt252>,
    );

    // ============ Keeper Functions ============

    fn process_deposits(ref self: TContractState, count: u32);
    fn mark_withdrawal_ready(ref self: TContractState, request_id: u256, usdc_amount: u256);
}

/// Withdrawal status enum values
pub mod WithdrawalStatus {
    pub const PENDING: u8 = 0;
    pub const PROCESSING: u8 = 1;
    pub const READY: u8 = 2;
    pub const COMPLETED: u8 = 3;
    pub const CANCELLED: u8 = 4;
}
