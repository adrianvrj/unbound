"use client";

import { useState, useEffect } from "react";
import { useAccount, useContract } from "@starknet-react/core";
import { CallData, cairo, Contract, RpcProvider } from "starknet";
import { CONTRACTS, VAULT_ABI } from "@/lib/contracts";
import { getQuote, buildSwapCalldata } from "@/lib/avnu";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";

interface UserWithdrawal {
    requestId: number;
    shares: bigint;
    usdcValue: number;
    status: number;
    timestamp: number;
}

const statusLabels: Record<number, { text: string; color: string }> = {
    0: { text: "Pending", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50" },
    1: { text: "Processing", color: "bg-blue-500/20 text-blue-400 border-blue-500/50" },
    2: { text: "Ready", color: "bg-highlight/10 text-highlight border-highlight/30" },
    3: { text: "Completed", color: "bg-gray-500/20 text-gray-400 border-gray-500/50" },
    4: { text: "Cancelled", color: "bg-red-500/20 text-red-400 border-red-500/50" }
};

export default function WithdrawalsPage() {
    const { address, account } = useAccount();
    const [withdrawals, setWithdrawals] = useState<UserWithdrawal[]>([]);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState<number | null>(null);
    const [message, setMessage] = useState("");

    const { contract: vaultContract } = useContract({
        abi: VAULT_ABI as any,
        address: CONTRACTS.VAULT as any,
    });

    const loadWithdrawals = async () => {
        if (!vaultContract || !address) return;

        setLoading(true);
        try {
            const queueLength = await vaultContract.call("get_withdrawal_queue_length", []) as any;
            const len = Number(queueLength);
            console.log("Withdrawal queue length:", len);

            const found: UserWithdrawal[] = [];

            for (let i = 0; i < len; i++) {
                const withdrawal = await vaultContract.call("get_pending_withdrawal", [cairo.uint256(i)]) as any;

                // Check if this withdrawal belongs to the current user
                if (BigInt(withdrawal[0]) === BigInt(address)) {
                    found.push({
                        requestId: i,
                        shares: BigInt(withdrawal[1]),
                        usdcValue: Number(withdrawal[3]) / 1e6,
                        status: Number(withdrawal[5]),
                        timestamp: Number(withdrawal[4])
                    });
                }
            }

            // Sort by requestId descending (newest first)
            found.sort((a, b) => b.requestId - a.requestId);
            setWithdrawals(found);
        } catch (e) {
            console.error("Failed to load withdrawals:", e);
        }
        setLoading(false);
    };

    useEffect(() => {
        loadWithdrawals();
    }, [vaultContract, address]);

    const handleComplete = async (requestId: number, usdcValue: number) => {
        if (!account || !vaultContract) return;

        setProcessing(requestId);
        setMessage("Getting swap quote...");

        try {
            // Get AVNU quote for USDC -> wBTC
            // Use VAULT address as taker since the vault executes the swap
            const usdcAmount = BigInt(Math.floor(usdcValue * 1e6));
            const quote = await getQuote(
                CONTRACTS.USDC,
                CONTRACTS.WBTC,
                usdcAmount,
                CONTRACTS.VAULT  // Vault is the taker, not user
            );

            if (!quote) {
                setMessage("Failed to get swap quote");
                setProcessing(null);
                return;
            }

            setMessage("Building swap transaction...");

            // Build swap calldata with vault as taker
            const swapData = await buildSwapCalldata(
                quote.quoteId,
                CONTRACTS.VAULT,  // Vault is the taker
                0.02 // 2% slippage
            );

            if (!swapData) {
                setMessage("Failed to build swap calldata");
                setProcessing(null);
                return;
            }

            setMessage("Submitting transaction...");

            // Call complete_withdraw
            // Find the multi_route_swap call (not the approve call which is usually first)
            const swapCall = swapData.calls.find(c => c.entrypoint === "multi_route_swap");
            if (!swapCall) {
                console.error("AVNU calls:", swapData.calls);
                setMessage("Error: No swap call found in AVNU response");
                setProcessing(null);
                return;
            }

            // Build calldata manually: request_id (u256 = low, high) + avnu_calldata (array_len, ...elements)
            const requestIdUint256 = cairo.uint256(requestId);
            const avnuCalldataArray = swapCall.calldata as string[];

            // Ensure all values are strings
            const manualCalldata = [
                requestIdUint256.low.toString(),
                requestIdUint256.high.toString(),
                avnuCalldataArray.length.toString(),
                ...avnuCalldataArray.map((v: any) => v.toString())
            ];

            console.log("Complete withdraw calldata:", {
                requestId,
                requestIdLow: requestIdUint256.low.toString(),
                requestIdHigh: requestIdUint256.high.toString(),
                avnuArrayLength: avnuCalldataArray.length,
                avnuFirstElements: avnuCalldataArray.slice(0, 5),
                fullCalldata: manualCalldata
            });

            const call = {
                contractAddress: CONTRACTS.VAULT,
                entrypoint: "complete_withdraw",
                calldata: manualCalldata
            };

            const result = await account.execute([call]);
            setMessage("Transaction submitted! Waiting for confirmation...");

            // Reload after a delay
            setTimeout(() => {
                loadWithdrawals();
                setMessage("Withdrawal completed!");
                setProcessing(null);
            }, 10000);

        } catch (e: any) {
            console.error("Complete withdrawal error:", e);
            setMessage(`Error: ${e.message || "Unknown error"}`);
            setProcessing(null);
        }
    };

    if (!address) {
        return (
            <div className="text-center py-12">
                <p className="text-muted text-lg">Connect your wallet to view withdrawals</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="text-center py-12">
                <p className="text-muted text-lg">Loading withdrawals...</p>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto">
            <div className="flex justify-between items-center mb-6 sm:mb-8">
                <h1 className="text-xl sm:text-2xl font-bold">Withdrawals</h1>
                <button
                    onClick={loadWithdrawals}
                    className="text-sm text-muted hover:text-white transition-colors"
                >
                    Refresh
                </button>
            </div>

            {withdrawals.length === 0 ? (
                <div className="text-center py-12 bg-card rounded-xl">
                    <p className="text-muted mb-4">No pending withdrawals</p>
                    <a href="/your-position" className="btn-primary inline-block text-sm">
                        Go to Your Position
                    </a>
                </div>
            ) : (
                <div className="space-y-4">
                    {withdrawals.map((w) => {
                        const statusInfo = statusLabels[w.status] || { text: "Unknown", color: "bg-gray-500/20 text-gray-400" };

                        return (
                            <div key={w.requestId} className="bg-card rounded-xl p-4 sm:p-6 border border-[#2a2a2a]">
                                <div className="flex justify-between items-start mb-3 sm:mb-4">
                                    <div>
                                        <span className="text-muted text-xs sm:text-sm">Request #{w.requestId}</span>
                                        <p className="font-data text-xl sm:text-2xl text-white mt-1">
                                            {(Number(w.shares) / 1e6).toFixed(4)} shares
                                        </p>
                                        <p className="text-highlight text-base sm:text-lg">${w.usdcValue.toFixed(2)} USDC</p>
                                    </div>
                                    <span className={`text-xs sm:text-sm px-2 sm:px-3 py-1 rounded-full border ${statusInfo.color}`}>
                                        {statusInfo.text}
                                    </span>
                                </div>

                                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-4 border-t border-[#2a2a2a]">
                                    <span className="text-muted text-xs">
                                        {new Date(w.timestamp * 1000).toLocaleString()}
                                    </span>

                                    {w.status === 2 && (
                                        <button
                                            onClick={() => handleComplete(w.requestId, w.usdcValue)}
                                            disabled={processing !== null}
                                            className="btn-primary w-full sm:w-auto px-4 sm:px-6 py-2 text-sm disabled:opacity-50"
                                        >
                                            {processing === w.requestId ? "Processing..." : "Complete"}
                                        </button>
                                    )}

                                    {w.status === 0 && (
                                        <span className="flex items-center gap-2 text-yellow-400 text-sm">
                                            <span className="w-3 h-3 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin"></span>
                                            Waiting for operator...
                                        </span>
                                    )}

                                    {w.status === 3 && (
                                        <span className="text-gray-400 text-sm">Completed</span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {message && (
                <div className={`mt-6 p-4 rounded-lg text-sm ${message.includes("Error") ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-green-500/10 text-green-400 border border-green-500/20"}`}>
                    {message}
                </div>
            )}

            <div className="mt-8 text-center">
                <a href="/your-position" className="text-muted hover:text-white text-sm transition-colors">
                    Back to Your Position
                </a>
            </div>
        </div>
    );
}
