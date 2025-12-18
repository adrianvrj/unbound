use snforge_std::{ContractClassTrait, DeclareResultTrait, declare};
use starknet::ContractAddress;
use unbound::unbound_vault::{IUnboundVaultDispatcher, IUnboundVaultDispatcherTrait};

// Mock addresses
#[feature("deprecated-starknet-consts")]
fn VESU_POOL() -> ContractAddress {
    starknet::contract_address_const::<'vesu_pool'>()
}

#[feature("deprecated-starknet-consts")]
fn WBTC() -> ContractAddress {
    starknet::contract_address_const::<'wbtc'>()
}

#[feature("deprecated-starknet-consts")]
fn USDC() -> ContractAddress {
    starknet::contract_address_const::<'usdc'>()
}

#[feature("deprecated-starknet-consts")]
fn USER() -> ContractAddress {
    starknet::contract_address_const::<'user'>()
}

#[feature("deprecated-starknet-consts")]
fn SWAP_ROUTER() -> ContractAddress {
    starknet::contract_address_const::<'swap_router'>()
}

fn deploy_vault() -> ContractAddress {
    let contract = declare("UnboundVault").unwrap().contract_class();
    let constructor_args = array![
        VESU_POOL().into(), SWAP_ROUTER().into(), WBTC().into(), USDC().into(),
    ];
    let (contract_address, _) = contract.deploy(@constructor_args).unwrap();
    contract_address
}

#[test]
fn test_vault_deployment() {
    let vault_address = deploy_vault();
    let vault = IUnboundVaultDispatcher { contract_address: vault_address };

    // Check total_assets is 0 initially
    let total = vault.total_assets();
    assert(total == 0, 'Initial assets should be 0');
}

#[test]
fn test_total_assets_initial_zero() {
    let vault_address = deploy_vault();
    let vault = IUnboundVaultDispatcher { contract_address: vault_address };

    assert(vault.total_assets() == 0, 'Should be zero');
}
