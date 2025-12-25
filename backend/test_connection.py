#!/usr/bin/env python3
"""
Test script to validate Extended API connection.
Run this after setting up your .env file with API keys.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extended_client import ExtendedClient
from src.config import settings


async def main():
    print("=" * 60)
    print("Extended API Connection Test")
    print("=" * 60)
    print()
    
    client = ExtendedClient()
    
    # Test 1: Public endpoint (no auth required)
    print("1. Testing public endpoint (funding rate)...")
    try:
        funding = await client.get_funding_rate("BTC-USD")
        apy_estimate = funding * 24 * 365 * 100  # Hourly rate -> Annual %
        print(f"   ✅ Current BTC-USD funding rate: {funding * 100:.6f}% per hour")
        print(f"   ✅ Estimated APY at 1x: {apy_estimate:.2f}%")
        print(f"   ✅ Estimated APY at 2x: {apy_estimate * 2:.2f}%")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        await client.close()
        return
    
    print()
    
    # Test 2: Get market info
    print("2. Getting BTC-USD market info...")
    try:
        market = await client.get_markets("BTC-USD")
        stats = market.get("marketStats", {})
        print(f"   ✅ Mark Price: ${float(stats.get('markPrice', 0)):,.2f}")
        print(f"   ✅ Index Price: ${float(stats.get('indexPrice', 0)):,.2f}")
        print(f"   ✅ Open Interest: {stats.get('openInterest', 'N/A')} BTC")
        
        config = market.get("tradingConfig", {})
        print(f"   ✅ Max Leverage: {config.get('maxLeverage', 'N/A')}x")
        print(f"   ✅ Min Order Size: {config.get('minOrderSize', 'N/A')} BTC")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print()
    
    # Test 3: Private endpoints (requires API key)
    if not settings.extended_api_key:
        print("3. Skipping private endpoints (no API key configured)")
        print("   ℹ️  Set EXTENDED_API_KEY in .env to test private endpoints")
    else:
        print("3. Testing private endpoints...")
        try:
            balance = await client.get_balance()
            if balance:
                print(f"   ✅ Account Balance: ${balance.balance:,.2f}")
                print(f"   ✅ Equity: ${balance.equity:,.2f}")
                print(f"   ✅ Available for Trade: ${balance.available_for_trade:,.2f}")
                print(f"   ✅ Margin Ratio: {balance.margin_ratio:.2f}%")
            else:
                print("   ⚠️  Balance is 0 or account not funded")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        print()
        
        # Test 4: Check positions
        print("4. Checking open positions...")
        try:
            positions = await client.get_positions("BTC-USD")
            if positions:
                for pos in positions:
                    print(f"   ✅ {pos.side} {pos.size} BTC @ {pos.leverage}x leverage")
                    print(f"      Unrealized PnL: ${pos.unrealised_pnl:,.2f}")
            else:
                print("   ✅ No open positions")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print()
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
