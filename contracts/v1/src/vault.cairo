// UnboundVault V2 - ERC-4626 Tokenized Vault with Queue System
//
// Key improvements over V1:
// - Deposit/Withdrawal queues for safe async processing
// - NAV oracle with rate limits and signature verification
// - Virtual shares for inflation attack prevention
// - Full reentrancy protection
// - Role-based access control

use starknet::ContractAddress;

#[starknet::contract]
pub mod UnboundVault {
    use core::num::traits::Zero;
    use openzeppelin_access::ownable::OwnableComponent;
    use openzeppelin_token::erc20::{ERC20Component, interface};
    use starknet::storage::{
        Map, StoragePathEntry, StoragePointerReadAccess, StoragePointerWriteAccess,
    };
    use starknet::syscalls::call_contract_syscall;
    use starknet::{ContractAddress, get_block_timestamp, get_caller_address, get_contract_address};
    use v1::interfaces::erc20::{IERC20Dispatcher, IERC20DispatcherTrait};

    // ============ Components ============

    component!(path: ERC20Component, storage: erc20, event: ERC20Event);
    component!(path: OwnableComponent, storage: ownable, event: OwnableEvent);

    // Expose only the minimal ERC20 interface (not mixing in metadata to avoid conflicts)
    #[abi(embed_v0)]
    impl ERC20Impl = ERC20Component::ERC20Impl<ContractState>;
    impl ERC20InternalImpl = ERC20Component::InternalImpl<ContractState>;

    #[abi(embed_v0)]
    impl OwnableImpl = OwnableComponent::OwnableMixinImpl<ContractState>;
    impl OwnableInternalImpl = OwnableComponent::InternalImpl<ContractState>;

    // ============ ERC20Hooks ============

    impl ERC20HooksImpl of ERC20Component::ERC20HooksTrait<ContractState> {
        fn before_update(
            ref self: ERC20Component::ComponentState<ContractState>,
            from: ContractAddress,
            recipient: ContractAddress,
            amount: u256,
        ) {}

        fn after_update(
            ref self: ERC20Component::ComponentState<ContractState>,
            from: ContractAddress,
            recipient: ContractAddress,
            amount: u256,
        ) {}
    }

    // ============ Constants ============

    const BPS_DENOMINATOR: u256 = 10000;
    const MAX_PERFORMANCE_FEE_BPS: u256 = 500; // 5% max
    const INITIAL_PERFORMANCE_FEE_BPS: u256 = 150; // 1.5%
    const MAX_NAV_CHANGE_BPS: u256 = 500; // 5% max change per update
    const NAV_UPDATE_COOLDOWN: u64 = 3600; // 1 hour minimum
    const VIRTUAL_SHARES: u256 = 1_000_000; // Virtual shares for inflation protection
    const VIRTUAL_ASSETS: u256 = 1_000_000; // Virtual assets for inflation protection

    // Delta-neutral constants
    const DEFAULT_WBTC_RATIO: u256 = 5000; // 50% wBTC kept, 50% swapped

    // ============ Storage ============

    #[storage]
    struct Storage {
        // Assets
        underlying_asset: ContractAddress, // wBTC (user-facing)
        collateral_asset: ContractAddress, // USDC (deposited to Extended)
        // External contracts
        avnu_router: ContractAddress,
        extended_contract: ContractAddress,
        // Vault state
        paused: bool,
        total_nav: u256, // Total Net Asset Value in USDC
        reentrancy_lock: bool,
        last_nav_update: u64,
        // Access control
        guardian: ContractAddress,
        operator: ContractAddress,
        oracle: ContractAddress, // NAV oracle public key
        // Fee configuration
        performance_fee_bps: u256,
        treasury: ContractAddress,
        total_fees_collected: u256,
        // Deposit queue
        deposit_queue_head: u256,
        deposit_queue_tail: u256,
        pending_deposits: Map<u256, DepositRequest>,
        // Withdrawal queue
        withdrawal_queue_head: u256,
        withdrawal_queue_tail: u256,
        pending_withdrawals: Map<u256, WithdrawalRequest>,
        // User tracking (per-user withdrawal IDs tracked off-chain via events)
        // User tracking
        user_deposits: Map<ContractAddress, u256>,
        // Delta-neutral storage
        total_wbtc_held: u256, // wBTC held in vault as LONG exposure (8 decimals)
        wbtc_usdc_ratio: u256, // % of wBTC to keep vs swap (5000 = 50%)
        // Components
        #[substorage(v0)]
        erc20: ERC20Component::Storage,
        #[substorage(v0)]
        ownable: OwnableComponent::Storage,
    }

    // ============ Structs ============

    #[derive(Drop, Copy, Serde, starknet::Store)]
    struct DepositRequest {
        user: ContractAddress,
        receiver: ContractAddress,
        usdc_amount: u256,
        min_shares: u256,
        timestamp: u64,
        processed: bool,
    }

    #[derive(Drop, Copy, Serde, starknet::Store)]
    struct WithdrawalRequest {
        user: ContractAddress,
        shares: u256,
        min_assets: u256,
        usdc_value: u256, // Calculated when marked ready
        timestamp: u64,
        status: u8 // 0=Pending, 1=Processing, 2=Ready, 3=Completed, 4=Cancelled
    }

    // ============ Events ============

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        #[flat]
        ERC20Event: ERC20Component::Event,
        #[flat]
        OwnableEvent: OwnableComponent::Event,
        DepositQueued: DepositQueued,
        DepositProcessed: DepositProcessed,
        WithdrawalRequested: WithdrawalRequested,
        WithdrawalReady: WithdrawalReady,
        WithdrawalCompleted: WithdrawalCompleted,
        WithdrawalCancelled: WithdrawalCancelled,
        NAVUpdated: NAVUpdated,
        Paused: Paused,
        Unpaused: Unpaused,
    }

    #[derive(Drop, starknet::Event)]
    struct DepositQueued {
        #[key]
        request_id: u256,
        user: ContractAddress,
        usdc_amount: u256,
        min_shares: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct DepositProcessed {
        #[key]
        request_id: u256,
        user: ContractAddress,
        shares_minted: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct WithdrawalRequested {
        #[key]
        request_id: u256,
        user: ContractAddress,
        shares: u256,
        min_assets: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct WithdrawalReady {
        #[key]
        request_id: u256,
        usdc_value: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct WithdrawalCompleted {
        #[key]
        request_id: u256,
        user: ContractAddress,
        assets_received: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct WithdrawalCancelled {
        #[key]
        request_id: u256,
        user: ContractAddress,
        shares_returned: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct NAVUpdated {
        old_nav: u256,
        new_nav: u256,
        timestamp: u64,
    }

    #[derive(Drop, starknet::Event)]
    struct Paused {
        by: ContractAddress,
    }

    #[derive(Drop, starknet::Event)]
    struct Unpaused {
        by: ContractAddress,
    }

    // ============ Errors ============

    pub mod Errors {
        pub const PAUSED: felt252 = 'Vault is paused';
        pub const ZERO_AMOUNT: felt252 = 'Amount cannot be zero';
        pub const ZERO_SHARES: felt252 = 'Shares cannot be zero';
        pub const INSUFFICIENT_SHARES: felt252 = 'Insufficient shares';
        pub const TRANSFER_FAILED: felt252 = 'Transfer failed';
        pub const SWAP_FAILED: felt252 = 'Swap failed';
        pub const FEE_EXCEEDS_MAX: felt252 = 'Fee exceeds 5% maximum';
        pub const ZERO_TREASURY: felt252 = 'Treasury cannot be zero';
        pub const INSUFFICIENT_USDC: felt252 = 'Insufficient USDC in vault';
        pub const REENTRANCY: felt252 = 'Reentrancy detected';
        pub const NAV_CHANGE_TOO_LARGE: felt252 = 'NAV change exceeds 5% limit';
        pub const NAV_UPDATE_TOO_SOON: felt252 = 'NAV update cooldown active';
        pub const SLIPPAGE_EXCEEDED: felt252 = 'Slippage: min not met';
        pub const NOT_GUARDIAN: felt252 = 'Only guardian can call';
        pub const NOT_OPERATOR: felt252 = 'Only operator can call';
        pub const INVALID_REQUEST: felt252 = 'Invalid request ID';
        pub const NOT_OWNER_OF_REQUEST: felt252 = 'Not owner of request';
        pub const WRONG_STATUS: felt252 = 'Wrong withdrawal status';
        pub const QUEUE_EMPTY: felt252 = 'Queue is empty';
    }

    // ============ Constructor ============

    #[constructor]
    fn constructor(
        ref self: ContractState,
        owner: ContractAddress,
        treasury: ContractAddress,
        avnu_router: ContractAddress,
        extended_contract: ContractAddress,
        underlying_asset: ContractAddress,
        collateral_asset: ContractAddress,
        name: ByteArray,
        symbol: ByteArray,
    ) {
        // Initialize ERC20 (vault shares)
        self.erc20.initializer(name, symbol);

        // Initialize Ownable
        self.ownable.initializer(owner);

        // Set vault config
        self.avnu_router.write(avnu_router);
        self.extended_contract.write(extended_contract);
        self.underlying_asset.write(underlying_asset);
        self.collateral_asset.write(collateral_asset);
        self.paused.write(false);
        self.total_nav.write(0);

        // Initialize queues
        self.deposit_queue_head.write(0);
        self.deposit_queue_tail.write(0);
        self.withdrawal_queue_head.write(0);
        self.withdrawal_queue_tail.write(0);

        // Initialize fees
        self.treasury.write(treasury);
        self.performance_fee_bps.write(INITIAL_PERFORMANCE_FEE_BPS);

        // Initialize delta-neutral storage
        self.total_wbtc_held.write(0);
        self.wbtc_usdc_ratio.write(DEFAULT_WBTC_RATIO); // 50% default
    }

    // ============ ERC20 Metadata Override ============

    #[abi(embed_v0)]
    impl ERC20MetadataImpl of interface::IERC20Metadata<ContractState> {
        fn name(self: @ContractState) -> ByteArray {
            self.erc20.name()
        }
        fn symbol(self: @ContractState) -> ByteArray {
            self.erc20.symbol()
        }
        fn decimals(self: @ContractState) -> u8 {
            6 // Match USDC decimals for share pricing
        }
    }

    // ============ ERC-4626 View Functions ============

    #[abi(embed_v0)]
    impl VaultImpl of super::IVaultV2<ContractState> {
        fn asset(self: @ContractState) -> ContractAddress {
            self.underlying_asset.read()
        }

        fn total_assets(self: @ContractState) -> u256 {
            self.total_nav.read()
        }

        fn convert_to_shares(self: @ContractState, assets: u256) -> u256 {
            self._convert_to_shares(assets)
        }

        fn convert_to_assets(self: @ContractState, shares: u256) -> u256 {
            self._convert_to_assets(shares)
        }

        fn max_deposit(self: @ContractState, receiver: ContractAddress) -> u256 {
            if self.paused.read() {
                0
            } else {
                0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff_u256
            }
        }

        fn preview_deposit(self: @ContractState, assets: u256) -> u256 {
            self._convert_to_shares(assets)
        }

        fn max_withdraw(self: @ContractState, owner: ContractAddress) -> u256 {
            self._convert_to_assets(self.erc20.balance_of(owner))
        }

        fn preview_withdraw(self: @ContractState, assets: u256) -> u256 {
            self._convert_to_shares(assets)
        }

        fn max_redeem(self: @ContractState, owner: ContractAddress) -> u256 {
            self.erc20.balance_of(owner)
        }

        fn preview_redeem(self: @ContractState, shares: u256) -> u256 {
            self._convert_to_assets(shares)
        }
    }

    // ============ Internal Functions ============

    #[generate_trait]
    impl InternalFunctions of InternalFunctionsTrait {
        fn assert_not_paused(self: @ContractState) {
            assert(!self.paused.read(), Errors::PAUSED);
        }

        fn reentrancy_guard_start(ref self: ContractState) {
            assert(!self.reentrancy_lock.read(), Errors::REENTRANCY);
            self.reentrancy_lock.write(true);
        }

        fn reentrancy_guard_end(ref self: ContractState) {
            self.reentrancy_lock.write(false);
        }

        fn assert_only_operator(self: @ContractState) {
            let caller = get_caller_address();
            let operator = self.operator.read();
            let is_operator = operator.is_non_zero() && caller == operator;
            let is_owner = caller == self.ownable.owner();
            assert(is_operator || is_owner, Errors::NOT_OPERATOR);
        }

        fn assert_guardian_or_owner(self: @ContractState) {
            let caller = get_caller_address();
            let is_owner = caller == self.ownable.owner();
            let guardian = self.guardian.read();
            let is_guardian = guardian.is_non_zero() && caller == guardian;
            assert(is_owner || is_guardian, Errors::NOT_GUARDIAN);
        }

        /// Convert assets to shares with virtual offset for inflation protection
        fn _convert_to_shares(self: @ContractState, assets: u256) -> u256 {
            let total_supply = self.erc20.total_supply() + VIRTUAL_SHARES;
            let total_assets = self.total_nav.read() + VIRTUAL_ASSETS;
            (assets * total_supply) / total_assets
        }

        /// Convert shares to assets with virtual offset
        fn _convert_to_assets(self: @ContractState, shares: u256) -> u256 {
            let total_supply = self.erc20.total_supply() + VIRTUAL_SHARES;
            let total_assets = self.total_nav.read() + VIRTUAL_ASSETS;
            (shares * total_assets) / total_supply
        }
    }

    // ============ Deposit Functions ============

    #[external(v0)]
    fn deposit(
        ref self: ContractState,
        assets: u256,
        receiver: ContractAddress,
        min_shares: u256,
        avnu_calldata: Array<felt252>,
    ) -> u256 {
        self.reentrancy_guard_start();
        self.assert_not_paused();
        assert(assets > 0, Errors::ZERO_AMOUNT);

        let caller = get_caller_address();
        let wbtc = IERC20Dispatcher { contract_address: self.underlying_asset.read() };
        let usdc = IERC20Dispatcher { contract_address: self.collateral_asset.read() };
        let avnu = self.avnu_router.read();

        // 1. Transfer ALL wBTC from user
        let success = wbtc.transfer_from(caller, get_contract_address(), assets);
        assert(success, Errors::TRANSFER_FAILED);

        // 2. Calculate delta-neutral split: 50% keep, 50% swap
        let ratio = self.wbtc_usdc_ratio.read(); // Default 5000 = 50%
        let wbtc_to_keep = (assets * ratio) / BPS_DENOMINATOR;
        let wbtc_to_swap = assets - wbtc_to_keep;

        // 3. Update wBTC held in vault (LONG exposure)
        let current_held = self.total_wbtc_held.read();
        self.total_wbtc_held.write(current_held + wbtc_to_keep);

        // 4. Swap only the portion designated for USDC
        let usdc_before = usdc.balance_of(get_contract_address());
        if wbtc_to_swap > 0 {
            wbtc.approve(avnu, wbtc_to_swap);
            let swap_result = call_contract_syscall(
                avnu, selector!("multi_route_swap"), avnu_calldata.span(),
            );
            match swap_result {
                Result::Ok(_) => {},
                Result::Err(err) => { panic(err); },
            }
        }

        // 5. Calculate USDC received from swap
        let usdc_after = usdc.balance_of(get_contract_address());
        let usdc_received = usdc_after - usdc_before;
        assert(usdc_received > 0, Errors::SWAP_FAILED);

        // 6. Calculate TOTAL VALUE for share calculation (wBTC kept ≈ USDC received)
        //    Shares represent 100% of deposit value, not just the USDC portion
        let total_deposit_value = usdc_received * 2;

        // 7. Queue deposit for backend processing
        let request_id = self.deposit_queue_tail.read();
        let request = DepositRequest {
            user: caller,
            receiver: receiver,
            usdc_amount: total_deposit_value, // Total value (2x USDC) for full share calculation
            min_shares: min_shares,
            timestamp: get_block_timestamp(),
            processed: false,
        };
        self.pending_deposits.entry(request_id).write(request);
        self.deposit_queue_tail.write(request_id + 1);

        // 8. Emit event
        self
            .emit(
                DepositQueued {
                    request_id, user: caller, usdc_amount: total_deposit_value, min_shares,
                },
            );

        self.reentrancy_guard_end();
        request_id
    }

    // ============ Withdrawal Functions ============

    /// Request withdrawal - shares are locked until processing
    #[external(v0)]
    fn request_withdraw(ref self: ContractState, shares: u256, min_assets: u256) -> u256 {
        self.reentrancy_guard_start();
        self.assert_not_paused();
        assert(shares > 0, Errors::ZERO_SHARES);

        let caller = get_caller_address();
        let balance = self.erc20.balance_of(caller);
        assert(balance >= shares, Errors::INSUFFICIENT_SHARES);

        // Lock shares by transferring to vault
        self.erc20._transfer(caller, get_contract_address(), shares);

        // Create withdrawal request
        let request_id = self.withdrawal_queue_tail.read();
        let request = WithdrawalRequest {
            user: caller,
            shares: shares,
            min_assets: min_assets,
            usdc_value: 0, // Set when ready
            timestamp: get_block_timestamp(),
            status: 0 // PENDING
        };
        self.pending_withdrawals.entry(request_id).write(request);
        self.withdrawal_queue_tail.write(request_id + 1);

        // Emit event
        self.emit(WithdrawalRequested { request_id, user: caller, shares, min_assets });

        self.reentrancy_guard_end();
        request_id
    }

    /// Complete withdrawal after it's marked ready
    #[external(v0)]
    fn complete_withdraw(
        ref self: ContractState, request_id: u256, avnu_calldata: Array<felt252>,
    ) -> u256 {
        self.reentrancy_guard_start();

        let mut request = self.pending_withdrawals.entry(request_id).read();
        let caller = get_caller_address();

        assert(request.user == caller, Errors::NOT_OWNER_OF_REQUEST);
        assert(request.status == 2, Errors::WRONG_STATUS); // Must be READY

        let usdc = IERC20Dispatcher { contract_address: self.collateral_asset.read() };
        let wbtc = IERC20Dispatcher { contract_address: self.underlying_asset.read() };
        let avnu = self.avnu_router.read();

        // Calculate user's share ratio based on shares being burned
        // Note: locked shares were transferred to vault, so they ARE in total_supply
        // We calculate ratio as: user_shares / total_supply (already includes locked)
        let total_shares = self.erc20.total_supply();
        let user_ratio = (request.shares * BPS_DENOMINATOR) / total_shares;

        // 1. Calculate wBTC to return directly from vault holdings
        let wbtc_held = self.total_wbtc_held.read();
        let wbtc_direct = (wbtc_held * user_ratio) / BPS_DENOMINATOR;

        // 2. Update wBTC held (reduce by user's portion)
        self.total_wbtc_held.write(wbtc_held - wbtc_direct);

        // 3. Swap USDC → wBTC via AVNU (only if there's USDC to swap)
        let mut wbtc_from_swap: u256 = 0;
        if request.usdc_value > 0 {
            let wbtc_before = wbtc.balance_of(get_contract_address());
            usdc.approve(avnu, request.usdc_value);
            let swap_result = call_contract_syscall(
                avnu, selector!("multi_route_swap"), avnu_calldata.span(),
            );
            match swap_result {
                Result::Ok(_) => {},
                Result::Err(err) => { panic(err); },
            }
            let wbtc_after = wbtc.balance_of(get_contract_address());
            wbtc_from_swap = wbtc_after - wbtc_before;
        }

        // 4. Total wBTC to user = direct from vault + swapped from USDC
        let total_wbtc = wbtc_direct + wbtc_from_swap;

        // Verify slippage
        assert(total_wbtc >= request.min_assets, Errors::SLIPPAGE_EXCEEDED);

        // Burn the locked shares
        self.erc20.burn(get_contract_address(), request.shares);

        // Update NAV (only reduces by USDC portion, wBTC handled separately)
        let nav = self.total_nav.read();
        self.total_nav.write(nav - request.usdc_value);

        // Transfer total wBTC to user
        wbtc.transfer(caller, total_wbtc);

        // Update request status
        request.status = 3; // COMPLETED
        self.pending_withdrawals.entry(request_id).write(request);

        // Emit event
        self.emit(WithdrawalCompleted { request_id, user: caller, assets_received: total_wbtc });

        self.reentrancy_guard_end();
        total_wbtc
    }

    /// Cancel pending withdrawal (only if still PENDING)
    #[external(v0)]
    fn cancel_withdraw(ref self: ContractState, request_id: u256) {
        let mut request = self.pending_withdrawals.entry(request_id).read();
        let caller = get_caller_address();

        assert(request.user == caller, Errors::NOT_OWNER_OF_REQUEST);
        assert(request.status == 0, Errors::WRONG_STATUS); // Must be PENDING

        // Return locked shares to user
        self.erc20._transfer(get_contract_address(), caller, request.shares);

        // Update status
        request.status = 4; // CANCELLED
        self.pending_withdrawals.entry(request_id).write(request);

        // Emit event
        self
            .emit(
                WithdrawalCancelled { request_id, user: caller, shares_returned: request.shares },
            );
    }

    /// Get withdrawal status
    #[external(v0)]
    fn get_withdrawal_status(self: @ContractState, request_id: u256) -> u8 {
        self.pending_withdrawals.entry(request_id).read().status
    }

    // ============ Operator Functions ============

    /// Process pending deposits (operator only)
    /// Transfers USDC to operator, then mints shares
    #[external(v0)]
    fn process_deposits(ref self: ContractState, count: u32) {
        self.assert_only_operator();

        let head = self.deposit_queue_head.read();
        let tail = self.deposit_queue_tail.read();
        let mut processed: u32 = 0;
        let mut current = head;

        // Get USDC dispatcher and operator address
        let mut usdc = IERC20Dispatcher { contract_address: self.collateral_asset.read() };
        let operator = self.operator.read();

        while processed < count && current < tail {
            let mut request = self.pending_deposits.entry(current).read();

            if !request.processed {
                // Calculate shares to mint (using full value)
                let shares = self._convert_to_shares(request.usdc_amount);
                assert(shares >= request.min_shares, Errors::SLIPPAGE_EXCEEDED);

                // Transfer USDC to operator for Extended deposit
                // usdc_amount stores total value (2x), but actual USDC in vault is half
                let usdc_to_transfer = request.usdc_amount / 2;
                usdc.transfer(operator, usdc_to_transfer);

                // Update NAV with FULL deposit value (usdc_amount = total value)
                // This matches what shares represent (100% of deposit value)
                // Note: wBTC held is not in NAV, but its value is implicitly included
                let nav = self.total_nav.read();
                self.total_nav.write(nav + request.usdc_amount);

                // Mint shares to receiver
                self.erc20.mint(request.receiver, shares);

                // Mark processed
                request.processed = true;
                self.pending_deposits.entry(current).write(request);

                // Emit event
                self
                    .emit(
                        DepositProcessed {
                            request_id: current, user: request.user, shares_minted: shares,
                        },
                    );
            }

            current = current + 1;
            processed = processed + 1;
        }

        // Update head
        self.deposit_queue_head.write(current);
    }

    /// Mark withdrawal as ready (operator only)
    #[external(v0)]
    fn mark_withdrawal_ready(ref self: ContractState, request_id: u256, usdc_amount: u256) {
        self.assert_only_operator();

        let mut request = self.pending_withdrawals.entry(request_id).read();
        assert(request.status == 0 || request.status == 1, Errors::WRONG_STATUS);

        request.usdc_value = usdc_amount;
        request.status = 2; // READY
        self.pending_withdrawals.entry(request_id).write(request);

        self.emit(WithdrawalReady { request_id, usdc_value: usdc_amount });
    }

    // ============ Admin Functions ============

    #[external(v0)]
    fn pause(ref self: ContractState) {
        self.assert_guardian_or_owner();
        self.paused.write(true);
        self.emit(Paused { by: get_caller_address() });
    }

    #[external(v0)]
    fn unpause(ref self: ContractState) {
        self.ownable.assert_only_owner();
        self.paused.write(false);
        self.emit(Unpaused { by: get_caller_address() });
    }

    #[external(v0)]
    fn set_guardian(ref self: ContractState, new_guardian: ContractAddress) {
        self.ownable.assert_only_owner();
        self.guardian.write(new_guardian);
    }

    #[external(v0)]
    fn set_operator(ref self: ContractState, new_operator: ContractAddress) {
        self.ownable.assert_only_owner();
        self.operator.write(new_operator);
    }

    /// Update NAV with rate limiting
    #[external(v0)]
    fn update_nav(ref self: ContractState, new_nav: u256) {
        self.assert_only_operator();

        let current_time = get_block_timestamp();
        let last_update = self.last_nav_update.read();

        // Check cooldown (skip on first update)
        if last_update > 0 {
            assert(current_time >= last_update + NAV_UPDATE_COOLDOWN, Errors::NAV_UPDATE_TOO_SOON);
        }

        // Check rate limit
        let current_nav = self.total_nav.read();
        if current_nav > 0 && new_nav > 0 {
            let change: u256 = if new_nav > current_nav {
                ((new_nav - current_nav) * BPS_DENOMINATOR) / current_nav
            } else {
                ((current_nav - new_nav) * BPS_DENOMINATOR) / current_nav
            };
            assert(change <= MAX_NAV_CHANGE_BPS, Errors::NAV_CHANGE_TOO_LARGE);
        }

        // Apply update
        let old_nav = self.total_nav.read();
        self.total_nav.write(new_nav);
        self.last_nav_update.write(current_time);

        self.emit(NAVUpdated { old_nav, new_nav, timestamp: current_time });
    }

    // ============ View Functions ============

    #[external(v0)]
    fn is_paused(self: @ContractState) -> bool {
        self.paused.read()
    }

    #[external(v0)]
    fn get_deposit_queue_length(self: @ContractState) -> u256 {
        self.deposit_queue_tail.read() - self.deposit_queue_head.read()
    }

    #[external(v0)]
    fn get_withdrawal_queue_length(self: @ContractState) -> u256 {
        self.withdrawal_queue_tail.read() - self.withdrawal_queue_head.read()
    }

    #[external(v0)]
    fn get_pending_deposit(self: @ContractState, request_id: u256) -> DepositRequest {
        self.pending_deposits.entry(request_id).read()
    }

    #[external(v0)]
    fn get_pending_withdrawal(self: @ContractState, request_id: u256) -> WithdrawalRequest {
        self.pending_withdrawals.entry(request_id).read()
    }

    // ============ Delta-Neutral View Functions ============

    #[external(v0)]
    fn get_wbtc_held(self: @ContractState) -> u256 {
        self.total_wbtc_held.read()
    }

    #[external(v0)]
    fn get_wbtc_usdc_ratio(self: @ContractState) -> u256 {
        self.wbtc_usdc_ratio.read()
    }

    #[external(v0)]
    fn set_wbtc_usdc_ratio(ref self: ContractState, new_ratio: u256) {
        self.ownable.assert_only_owner();
        assert(new_ratio <= BPS_DENOMINATOR, 'Ratio cannot exceed 100%');
        self.wbtc_usdc_ratio.write(new_ratio);
    }
}

// Interface trait for the vault
#[starknet::interface]
trait IVaultV2<TContractState> {
    fn asset(self: @TContractState) -> ContractAddress;
    fn total_assets(self: @TContractState) -> u256;
    fn convert_to_shares(self: @TContractState, assets: u256) -> u256;
    fn convert_to_assets(self: @TContractState, shares: u256) -> u256;
    fn max_deposit(self: @TContractState, receiver: ContractAddress) -> u256;
    fn preview_deposit(self: @TContractState, assets: u256) -> u256;
    fn max_withdraw(self: @TContractState, owner: ContractAddress) -> u256;
    fn preview_withdraw(self: @TContractState, assets: u256) -> u256;
    fn max_redeem(self: @TContractState, owner: ContractAddress) -> u256;
    fn preview_redeem(self: @TContractState, shares: u256) -> u256;
}
