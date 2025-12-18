#[starknet::interface]
pub trait IUnboundVault<TContractState> {
    fn deposit(
        ref self: TContractState,
        assets: u256,
        receiver: starknet::ContractAddress,
        leverage_factor: u256,
    );
    fn withdraw(
        ref self: TContractState,
        shares: u256,
        receiver: starknet::ContractAddress,
        owner: starknet::ContractAddress,
    );
    fn total_assets(self: @TContractState) -> u256;
}

#[starknet::contract]
pub mod UnboundVault {
    use alexandria_math::i257::I257Trait;
    use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
    use starknet::storage::{
        Map, StorageMapReadAccess, StorageMapWriteAccess, StoragePointerReadAccess,
        StoragePointerWriteAccess,
    };
    use starknet::{ContractAddress, get_caller_address, get_contract_address};
    use unbound::interfaces::avnu::{IAvnuExchangeDispatcher, IAvnuExchangeDispatcherTrait};
    use unbound::interfaces::vesu::{
        Amount, AmountDenomination, IFlashLoanReceiver, IPoolDispatcher, IPoolDispatcherTrait,
        ModifyPositionParams,
    };

    #[storage]
    struct Storage {
        vesu_pool: ContractAddress,
        swap_router: ContractAddress,
        asset: ContractAddress,
        debt_asset: ContractAddress,
        // ERC4626-like storage
        total_supply: u256,
        balances: Map<ContractAddress, u256>,
    }

    #[abi(embed_v0)]
    impl FlashLoanReceiverImpl of IFlashLoanReceiver<ContractState> {
        fn on_flash_loan(
            ref self: ContractState,
            sender: ContractAddress,
            asset: ContractAddress,
            amount: u256,
            data: Span<felt252>,
        ) {
            assert(sender == get_contract_address(), 'Only initiates by self');
            assert(get_caller_address() == self.vesu_pool.read(), 'Only Vesu Pool');

            let pool = IPoolDispatcher { contract_address: self.vesu_pool.read() };
            let collateral_asset = self.asset.read();
            let debt_asset = self.debt_asset.read();

            // 1. Swap Borrowed Debt Asset (e.g., USDC) -> Collateral Asset (e.g., WBTC)
            let debt_token = IERC20Dispatcher { contract_address: debt_asset };
            debt_token.approve(self.swap_router.read(), amount);

            let swap_router = IAvnuExchangeDispatcher { contract_address: self.swap_router.read() };

            // Execute swap via AVNU (empty routes = AVNU finds best route)
            swap_router
                .multi_route_swap(
                    debt_asset, // token_from
                    amount, // token_from_amount
                    collateral_asset, // token_to
                    0, // token_to_amount (0 = any)
                    1, // token_to_min_amount (1 = accept any, should use oracle in prod)
                    get_contract_address(), // beneficiary
                    0, // integrator_fee_amount_bps
                    get_contract_address(), // integrator_fee_recipient (unused)
                    array![] // routes (empty = AVNU router decides)
                );

            // 2. Get current collateral balance of this contract
            let collateral_token = IERC20Dispatcher { contract_address: collateral_asset };
            let total_collateral = collateral_token.balance_of(get_contract_address());

            // 3. Approve Vesu Pool to spend collateral
            collateral_token.approve(self.vesu_pool.read(), total_collateral);

            // 4. Supply Collateral + Borrow Debt in one modify_position call
            let collateral_amount = Amount {
                denomination: AmountDenomination::Assets,
                value: I257Trait::new(total_collateral, is_negative: false),
            };
            let debt_amount = Amount {
                denomination: AmountDenomination::Assets,
                value: I257Trait::new(amount, is_negative: false) // Borrow to repay flashloan
            };

            let params = ModifyPositionParams {
                collateral_asset: collateral_asset,
                debt_asset: debt_asset,
                user: get_contract_address(),
                collateral: collateral_amount,
                debt: debt_amount,
            };

            pool.modify_position(params);

            // 5. Approve debt asset to repay flashloan (Pool will pull it)
            let debt_token = IERC20Dispatcher { contract_address: debt_asset };
            debt_token.approve(self.vesu_pool.read(), amount);
        }
    }

    #[constructor]
    fn constructor(
        ref self: ContractState,
        vesu_pool: ContractAddress,
        swap_router: ContractAddress,
        asset: ContractAddress,
        debt_asset: ContractAddress,
    ) {
        self.vesu_pool.write(vesu_pool);
        self.swap_router.write(swap_router);
        self.asset.write(asset);
        self.debt_asset.write(debt_asset);
    }

    #[abi(embed_v0)]
    impl UnboundVaultImpl of super::IUnboundVault<ContractState> {
        fn deposit(
            ref self: ContractState, assets: u256, receiver: ContractAddress, leverage_factor: u256,
        ) {
            // 1. Transfer Assets from User to Vault
            let asset = self.asset.read();
            IERC20Dispatcher { contract_address: asset }
                .transfer_from(get_caller_address(), get_contract_address(), assets);

            // 2. Calculate Flashloan Amount (Debt to borrow)
            // Leverage 3x means: Collateral = 3 * Deposit. Debt = 2 * Deposit (approx).
            // Precise math: Equity = Deposit. Position = Deposit * L. Debt = Deposit * (L-1).
            // We need to borrow USDC worth of (Deposit * (L-1)).
            // For MVP, we pass explicit amount? No, we should rely on Oracle price.
            // For simplicity in this step, let's assume we flashloan the DEBT ASSET.

            let debt_amount_to_flashloan = assets; // Placeholder logic. Real logic needs price.

            let pool = IPoolDispatcher { contract_address: self.vesu_pool.read() };
            let debt_asset = self.debt_asset.read();

            // Trigger Flashloan
            pool
                .flash_loan(
                    get_contract_address(),
                    debt_asset,
                    debt_amount_to_flashloan,
                    false,
                    array![].span(),
                );

            // Mint Shares (Simplified ERC4626)
            self.balances.write(receiver, self.balances.read(receiver) + assets);
            self.total_supply.write(self.total_supply.read() + assets);
        }

        fn withdraw(
            ref self: ContractState,
            shares: u256,
            receiver: ContractAddress,
            owner: ContractAddress,
        ) {
            // 1. Verify ownership/delegation
            assert(get_caller_address() == owner, 'Not owner');
            assert(self.balances.read(owner) >= shares, 'Insufficient shares');

            let pool = IPoolDispatcher { contract_address: self.vesu_pool.read() };
            let collateral_asset = self.asset.read();
            let debt_asset = self.debt_asset.read();

            // 2. Calculate how much debt to repay (proportional to shares)
            // For MVP: assume 1:1 share to asset ratio
            let debt_to_repay = shares; // Placeholder

            // 3. Flashloan the debt asset to repay our Vesu position
            pool
                .flash_loan(
                    get_contract_address(),
                    debt_asset,
                    debt_to_repay,
                    false,
                    array!['withdraw'].span() // Signal this is a withdraw operation
                );

            // 4. Burn shares
            self.balances.write(owner, self.balances.read(owner) - shares);
            self.total_supply.write(self.total_supply.read() - shares);

            // 5. Transfer remaining collateral to receiver
            let collateral_token = IERC20Dispatcher { contract_address: collateral_asset };
            let vault_balance = collateral_token.balance_of(get_contract_address());
            collateral_token.transfer(receiver, vault_balance);
        }

        fn total_assets(self: @ContractState) -> u256 {
            // TODO: Implement Logic
            0
        }
    }
}
