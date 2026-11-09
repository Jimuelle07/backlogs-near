//! Mock NEP-141 "tUSDC" for the testnet demo. Owner-only mint, no storage deposit needed for mint.
use near_contract_standards::fungible_token::events::FtMint;
use near_contract_standards::fungible_token::metadata::{
    FungibleTokenMetadata, FungibleTokenMetadataProvider, FT_METADATA_SPEC,
};
use near_contract_standards::fungible_token::{
    FungibleToken, FungibleTokenCore, FungibleTokenResolver,
};
use near_contract_standards::storage_management::{
    StorageBalance, StorageBalanceBounds, StorageManagement,
};
use near_sdk::json_types::U128;
use near_sdk::store::LazyOption;
use near_sdk::{
    env, near, require, AccountId, BorshStorageKey, NearToken, PanicOnDefault, PromiseOrValue,
};

#[derive(BorshStorageKey)]
#[near]
enum StorageKey {
    Token,
    Metadata,
}

#[derive(PanicOnDefault)]
#[near(contract_state)]
pub struct Contract {
    owner_id: AccountId,
    token: FungibleToken,
    metadata: LazyOption<FungibleTokenMetadata>,
}

#[near]
impl Contract {
    #[init]
    pub fn new(owner_id: AccountId) -> Self {
        require!(!env::state_exists(), "Already initialized");
        Self {
            owner_id,
            token: FungibleToken::new(StorageKey::Token),
            metadata: LazyOption::new(
                StorageKey::Metadata,
                Some(FungibleTokenMetadata {
                    spec: FT_METADATA_SPEC.to_string(),
                    name: "Test USDC (backlogs-near)".to_string(),
                    symbol: "tUSDC".to_string(),
                    icon: None,
                    reference: None,
                    reference_hash: None,
                    decimals: 6,
                }),
            ),
        }
    }

    /// Owner-only mint. Registers `account_id` if needed (testnet mock: no storage deposit).
    pub fn mint(&mut self, account_id: AccountId, amount: U128) {
        require!(env::predecessor_account_id() == self.owner_id, "Only owner can mint");
        if self.token.accounts.get(&account_id).is_none() {
            self.token.internal_register_account(&account_id);
        }
        self.token.internal_deposit(&account_id, amount.into());
        FtMint { owner_id: &account_id, amount, memo: None }.emit();
    }
}

#[near]
impl FungibleTokenCore for Contract {
    #[payable]
    fn ft_transfer(&mut self, receiver_id: AccountId, amount: U128, memo: Option<String>) {
        self.token.ft_transfer(receiver_id, amount, memo)
    }

    #[payable]
    fn ft_transfer_call(
        &mut self,
        receiver_id: AccountId,
        amount: U128,
        memo: Option<String>,
        msg: String,
    ) -> PromiseOrValue<U128> {
        self.token.ft_transfer_call(receiver_id, amount, memo, msg)
    }

    fn ft_total_supply(&self) -> U128 {
        self.token.ft_total_supply()
    }

    fn ft_balance_of(&self, account_id: AccountId) -> U128 {
        self.token.ft_balance_of(account_id)
    }
}

#[near]
impl FungibleTokenResolver for Contract {
    #[private]
    fn ft_resolve_transfer(
        &mut self,
        sender_id: AccountId,
        receiver_id: AccountId,
        amount: U128,
    ) -> U128 {
        let (used, _burned) =
            self.token.internal_ft_resolve_transfer(&sender_id, receiver_id, amount);
        used.into()
    }
}

#[near]
impl StorageManagement for Contract {
    #[payable]
    fn storage_deposit(
        &mut self,
        account_id: Option<AccountId>,
        registration_only: Option<bool>,
    ) -> StorageBalance {
        self.token.storage_deposit(account_id, registration_only)
    }

    #[payable]
    fn storage_withdraw(&mut self, amount: Option<NearToken>) -> StorageBalance {
        self.token.storage_withdraw(amount)
    }

    #[payable]
    fn storage_unregister(&mut self, force: Option<bool>) -> bool {
        self.token.internal_storage_unregister(force).is_some()
    }

    fn storage_balance_bounds(&self) -> StorageBalanceBounds {
        self.token.storage_balance_bounds()
    }

    fn storage_balance_of(&self, account_id: AccountId) -> Option<StorageBalance> {
        self.token.storage_balance_of(account_id)
    }
}

#[near]
impl FungibleTokenMetadataProvider for Contract {
    fn ft_metadata(&self) -> FungibleTokenMetadata {
        self.metadata.get().clone().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use near_sdk::test_utils::{accounts, VMContextBuilder};
    use near_sdk::testing_env;

    fn ctx(predecessor: AccountId) {
        testing_env!(VMContextBuilder::new().predecessor_account_id(predecessor).build());
    }

    #[test]
    #[should_panic(expected = "Only owner can mint")]
    fn non_owner_mint_panics() {
        ctx(accounts(0));
        let mut c = Contract::new(accounts(0));
        ctx(accounts(1));
        c.mint(accounts(1), U128(5));
    }

    #[test]
    fn mint_registers_and_credits() {
        ctx(accounts(0));
        let mut c = Contract::new(accounts(0));
        assert!(c.token.accounts.get(&accounts(2)).is_none());
        c.mint(accounts(2), U128(1_000_000));
        assert_eq!(c.ft_balance_of(accounts(2)), U128(1_000_000));
        assert_eq!(c.ft_total_supply(), U128(1_000_000));
        c.mint(accounts(2), U128(1));
        assert_eq!(c.ft_balance_of(accounts(2)), U128(1_000_001));
    }

    #[test]
    fn metadata_decimals_is_6() {
        ctx(accounts(0));
        let c = Contract::new(accounts(0));
        let m = c.ft_metadata();
        assert_eq!(m.decimals, 6);
        assert_eq!(m.symbol, "tUSDC");
    }
}
