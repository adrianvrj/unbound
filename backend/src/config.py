"""
Configuration management for the Funding Rate Vault backend.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Extended API
    extended_api_key: str = ""
    extended_stark_key: str = ""
    extended_vault_number: str = ""
    
    # Extended endpoints (MAINNET)
    extended_api_url: str = "https://api.starknet.extended.exchange/api/v1"
    extended_ws_url: str = "wss://api.starknet.extended.exchange/stream.extended.exchange/v1"
    
    # Strategy settings
    leverage: float = 2.0  # 2x-5x, start conservative
    market: str = "BTC-USD"
    funding_threshold_open: float = 0.000001  # 0.0001% - open short when above (lowered for testing)
    funding_threshold_close: float = -0.000001  # -0.0001% - close when below
    rebalance_interval_seconds: int = 3600  # 1 hour
    
    # Vault contract (Starknet) - Delta-Neutral Vault v6 (wBTC distribution fix, 2024-12-24)
    vault_contract_address: str = "0x0291a1d4829bf8852aa5182409cc5b5f7c15a2709a5e5a5ff8e44791996acb62"
    starknet_rpc_url: str = "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_10/dql5pMT88iueZWl7L0yzT56uVk0EBU4L"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    admin_api_key: str = ""  # Set in .env as ADMIN_API_KEY for protected endpoints
    frontend_url: str = "http://localhost:3000"  # For CORS, set in .env for production
    
    # Operator wallet (for on-chain transactions)
    operator_address: str = "0x0244f12432e01EC3BE1F4c1E0fbC3e7db90a3EF06105F3568Daab5f1Fdb8ff07"
    operator_private_key: str = ""  # Set in .env as OPERATOR_PRIVATE_KEY
    
    # Extended deposit contract (for depositing USDC)
    extended_deposit_contract: str = "0x062da0780fae50d68cecaa5a051606dc21217ba290969b302db4dd99d2e9b470"
    usdc_contract: str = "0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
