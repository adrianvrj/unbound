// AVNU Exchange Interface - For token swaps on Starknet
// Mainnet Address: 0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f

use starknet::ContractAddress;

#[derive(Copy, Drop, Serde)]
pub struct Route {
    pub token_from: ContractAddress,
    pub token_to: ContractAddress,
    pub exchange_address: ContractAddress,
    pub percent: u128,
    pub additional_swap_params: Span<felt252>,
}

#[starknet::interface]
pub trait IAvnuExchange<TContractState> {
    fn multi_route_swap(
        ref self: TContractState,
        token_from_address: ContractAddress,
        token_from_amount: u256,
        token_to_address: ContractAddress,
        token_to_amount: u256,
        token_to_min_amount: u256,
        beneficiary: ContractAddress,
        integrator_fee_amount_bps: u128,
        integrator_fee_recipient: ContractAddress,
        routes: Array<Route>,
    ) -> bool;
}
