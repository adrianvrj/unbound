#!/usr/bin/env python3
"""
Main entry point for the Funding Rate Vault backend.
Runs both the API server and the rebalancer.
"""
import asyncio
import uvicorn
from src.api import app
from src.rebalancer import start_rebalancer
from src.config import settings


async def run_api():
    """Run the FastAPI server."""
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """
    Main entry point.
    Run API server only by default.
    Rebalancer can be started via API endpoint.
    """
    print("=" * 60)
    print("Funding Rate Vault Backend")
    print("=" * 60)
    print(f"API Server: http://{settings.api_host}:{settings.api_port}")
    print(f"Market: {settings.market}")
    print(f"Leverage: {settings.leverage}x")
    print(f"Rebalance Interval: {settings.rebalance_interval_seconds}s")
    print("=" * 60)
    print("\nStarting API server...")
    print("Use POST /api/rebalancer/start to start the rebalancer")
    print()
    
    await run_api()


if __name__ == "__main__":
    asyncio.run(main())
