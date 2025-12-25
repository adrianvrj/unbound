export interface VaultActivity {
    action: string;
    amount: string;
    txHash: string;
    timestamp: string;
}

const RPC_URL = "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_7/dql5pMT88iueZWl7L0yzT56uVk0EBU4L";

// Event key selectors (keccak of event name)
// You can get these by computing keccak256 of the event signature
const DEPOSIT_EVENT_KEY = "0x1dcde06aabdbca2f80aa51392b345d7549d7757aa855f7e37f5d335ac8243166";
const WITHDRAW_EVENT_KEY = "0x569f1e56d2d8e72de5e3c9e2f1d960e2f9b34d6be9c8ad8d3a39a79f2e2f3bad";

export async function getVaultEventsRPC(vaultAddress: string): Promise<VaultActivity[]> {
    try {
        console.log("Fetching events for vault:", vaultAddress);

        const response = await fetch(RPC_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "starknet_getEvents",
                params: {
                    filter: {
                        from_block: { block_number: 4590000 }, // Recent blocks
                        to_block: "latest",
                        address: vaultAddress,
                        chunk_size: 20
                    }
                },
                id: 1
            })
        });

        const data = await response.json();
        console.log("RPC response:", data);

        if (data.error) {
            console.error("RPC error:", data.error);
            return [];
        }

        if (!data.result || !data.result.events || data.result.events.length === 0) {
            console.log("No events found");
            return [];
        }

        const activities: VaultActivity[] = [];

        for (const event of data.result.events) {
            const selector = event.keys?.[0] || '';
            let action = 'Transaction';
            let amount = '';

            console.log("Event selector:", selector);
            console.log("Event data:", event.data);

            // Parse based on event type
            // For Deposit/DepositEvent: typically has assets amount in data
            // For Withdraw/WithdrawEvent: typically has assets amount in data
            if (event.data && event.data.length > 0) {
                // Try to parse the amount (usually the 3rd or 4th field)
                // Format varies by event but usually u256 is split into low/high
                try {
                    // Check event keys for common patterns
                    if (event.keys.length > 1) {
                        // Some events have the action type in keys
                        action = parseEventName(selector);
                    }

                    // Amount is usually in data[2] or data[3] for ERC-4626 events
                    if (event.data.length >= 3) {
                        const amountLow = BigInt(event.data[2] || "0");
                        const amountHigh = BigInt(event.data[3] || "0");
                        const amountRaw = amountLow + (amountHigh << BigInt(128));

                        if (amountRaw > BigInt(0)) {
                            // Check if it looks like wBTC (8 decimals) or USDC (6 decimals)
                            if (amountRaw < BigInt(1_000_000_000_000)) { // Likely wBTC
                                amount = (Number(amountRaw) / 1e8).toFixed(6) + ' WBTC';
                            } else {
                                amount = (Number(amountRaw) / 1e6).toFixed(2) + ' USDC';
                            }
                        }
                    }
                } catch (e) {
                    console.error("Error parsing event data:", e);
                }
            }

            activities.push({
                action,
                amount,
                txHash: event.transaction_hash || '',
                timestamp: event.block_number?.toString() || ''
            });
        }

        console.log("Parsed activities:", activities);
        return activities;
    } catch (error) {
        console.error("Error fetching events via RPC:", error);
        return [];
    }
}

function parseEventName(selector: string): string {
    // Map known selectors to action names
    const selectorMap: Record<string, string> = {
        // ERC-4626 Deposit event
        "0x1dcde06aabdbca2f80aa51392b345d7549d7757aa855f7e37f5d335ac8243166": "Deposit",
        // ERC-4626 Withdraw event
        "0x569f1e56d2d8e72de5e3c9e2f1d960e2f9b34d6be9c8ad8d3a39a79f2e2f3bad": "Withdraw",
        // Transfer event (common in ERC20)
        "0x99cd8bde557814842a3121e8ddfd433a539b8c9f14bf31ebf108d12e6196e9": "Transfer",
    };

    return selectorMap[selector] || "Transaction";
}
