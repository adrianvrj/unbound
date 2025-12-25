"use client";

import { useState, useEffect } from "react";
import { useAccount, useContract, useSendTransaction } from "@starknet-react/core";
import { CONTRACTS, VAULT_ABI } from "@/lib/contracts";
import { getVaultStatus, VaultStatus } from "@/lib/backend-api";
import { cairo, CallData } from "starknet";
import { getSwapCalldata } from "@/lib/avnu";
import { useToast } from "@/components/Toast";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";

interface WithdrawalStatus {
    extended_available: number;
    operator_balance: number;
    vault_total_usdc: number;
    vault_total_shares: number;
    has_positions: boolean;
}

export default function YourPositionPage() {
    const { address, account } = useAccount();
    const { showToast, updateToast } = useToast();
    const [shares, setShares] = useState<bigint>(BigInt(0));
    const [shareValue, setShareValue] = useState<bigint>(BigInt(0));
    const [totalUsdc, setTotalUsdc] = useState<bigint>(BigInt(0));
    const [loading, setLoading] = useState(false);
    const [vaultStatus, setVaultStatus] = useState<VaultStatus | null>(null);
    const [withdrawalStatus, setWithdrawalStatus] = useState<WithdrawalStatus | null>(null);
    const [withdrawing, setWithdrawing] = useState(false);
    const [withdrawMessage, setWithdrawMessage] = useState("");

    // Withdrawal form states
    const [withdrawAmountShares, setWithdrawAmountShares] = useState<string>("");
    const [recipientAddress, setRecipientAddress] = useState<string>("");

    const { contract: vaultContract } = useContract({
        abi: VAULT_ABI as any,
        address: CONTRACTS.VAULT as any,
    });

    // V2 withdrawal tracking
    const [pendingWithdrawalId, setPendingWithdrawalId] = useState<number | null>(null);
    const [pendingWithdrawalStatus, setPendingWithdrawalStatus] = useState<number>(0); // 0=PENDING, 2=READY
    const [pollingWithdrawal, setPollingWithdrawal] = useState(false);

    // User's withdrawals list for queue view
    interface UserWithdrawal {
        requestId: number;
        shares: bigint;
        usdcValue: number;
        status: number; // 0=PENDING, 1=PROCESSING, 2=READY, 3=COMPLETED, 4=CANCELLED
        timestamp: number;
    }
    const [userWithdrawals, setUserWithdrawals] = useState<UserWithdrawal[]>([]);

    // Load position on mount
    const loadPosition = async () => {
        if (!vaultContract || !address) return;
        try {
            setLoading(true);

            // Get user's shares
            const sharesResult = await vaultContract.call("balance_of", [address]) as any;
            const sharesBigInt = BigInt(sharesResult);
            setShares(sharesBigInt);
            setWithdrawAmountShares((Number(sharesBigInt) / 1e6).toString());
            setRecipientAddress(address);

            // Get value of shares in USDC
            const valueResult = await vaultContract.call("preview_redeem", [cairo.uint256(sharesBigInt)]) as any;
            setShareValue(BigInt(valueResult));

            // Get total USDC in vault
            const totalResult = await vaultContract.call("total_assets", []) as any;
            setTotalUsdc(BigInt(totalResult));

            // Get backend status
            const status = await getVaultStatus();
            if (status) setVaultStatus(status);

            // Get withdrawal status
            try {
                const resp = await fetch(`${BACKEND_URL}/api/withdrawal/status`);
                if (resp.ok) {
                    const data = await resp.json();
                    setWithdrawalStatus(data);
                }
            } catch (e) {
                console.error("Failed to get withdrawal status:", e);
            }

            // Check for pending user withdrawals in the queue
            try {
                const queueLength = await vaultContract.call("get_withdrawal_queue_length", []) as any;
                const len = Number(queueLength);
                console.log("Checking withdrawal queue, length:", len);

                const withdrawalsFound: UserWithdrawal[] = [];
                let foundPending = false;

                for (let i = 0; i < len; i++) {
                    const withdrawal = await vaultContract.call("get_pending_withdrawal", [cairo.uint256(i)]) as any;
                    // [0]=user, [1]=shares, [2]=min_assets, [3]=usdc_value, [4]=timestamp, [5]=status
                    console.log(`  Withdrawal #${i}: user=${withdrawal[0]}, status=${withdrawal[5]}`);

                    // Check if this withdrawal belongs to the current user
                    if (BigInt(withdrawal[0]) === BigInt(address)) {
                        const status = Number(withdrawal[5]);
                        const shares = BigInt(withdrawal[1]);
                        const usdcValue = Number(withdrawal[3]) / 1e6;
                        const timestamp = Number(withdrawal[4]);

                        withdrawalsFound.push({
                            requestId: i,
                            shares,
                            usdcValue,
                            status,
                            timestamp
                        });

                        // Track first actionable withdrawal
                        if (!foundPending && (status === 0 || status === 2)) {
                            console.log(`  Found actionable withdrawal #${i}, status=${status}`);
                            setPendingWithdrawalId(i);
                            setWithdrawRequestId(i.toString());
                            setPendingWithdrawalStatus(status);
                            if (status === 0) {
                                setPollingWithdrawal(true);
                            }
                            foundPending = true;
                        }
                    }
                }

                setUserWithdrawals(withdrawalsFound);
                console.log(`Found ${withdrawalsFound.length} withdrawals for user`);
            } catch (e) {
                console.error("Failed to check withdrawal queue:", e);
            }

        } catch (e) {
            console.error("Failed to load position:", e);
        }
        setLoading(false);
    };

    // Load position on mount
    useEffect(() => {
        loadPosition();
    }, [vaultContract, address]);

    const requestWithdrawal = async () => {
        if (!vaultContract || !address || !account) return;
        if (shares === BigInt(0)) return;

        const sharesToBurn = parseFloat(withdrawAmountShares);
        if (isNaN(sharesToBurn) || sharesToBurn <= 0) {
            setWithdrawMessage("❌ Invalid amount");
            return;
        }

        setWithdrawing(true);
        setWithdrawMessage("Requesting withdrawal on-chain...");

        try {
            // Convert to raw shares (6 decimals)
            const sharesRaw = BigInt(Math.floor(sharesToBurn * 1e6));

            // Call request_withdraw on the vault contract
            // min_assets = 0 for no slippage protection (user already saw preview)
            const call = {
                contractAddress: CONTRACTS.VAULT,
                entrypoint: "request_withdraw",
                calldata: CallData.compile({
                    shares: cairo.uint256(sharesRaw),
                    min_assets: cairo.uint256(0) // No slippage protection for now
                })
            };

            const result = await account.execute([call]);
            showToast({
                type: "success",
                title: "Withdrawal Requested!",
                txHash: result.transaction_hash
            });

            // Get the request_id from the withdrawal queue length - 1
            // (The new request is the last one added)
            const queueLength = await vaultContract.call("get_withdrawal_queue_length", []) as any;
            const requestId = Number(queueLength) - 1;

            setPendingWithdrawalId(requestId);
            setWithdrawRequestId(requestId.toString());
            setPendingWithdrawalStatus(0); // PENDING

            // Start polling for status
            setPollingWithdrawal(true);

        } catch (e: any) {
            console.error("Withdrawal error:", e);
            showToast({ type: "error", title: "Withdrawal Failed", message: e.message });
        }

        setWithdrawing(false);
    };

    // Poll withdrawal status every 10s when waiting
    useEffect(() => {
        if (!pollingWithdrawal || pendingWithdrawalId === null || !vaultContract) return;

        const checkStatus = async () => {
            try {
                const status = await vaultContract.call("get_withdrawal_status", [cairo.uint256(pendingWithdrawalId)]) as any;
                const statusNum = Number(status);
                setPendingWithdrawalStatus(statusNum);

                if (statusNum === 2) { // READY
                    setWithdrawMessage("✅ Withdrawal ready! Click 'Complete Withdrawal' to receive wBTC");
                    setPollingWithdrawal(false);
                } else if (statusNum === 3 || statusNum === 4) { // COMPLETED or CANCELLED
                    setPollingWithdrawal(false);
                }
            } catch (e) {
                console.error("Error checking withdrawal status:", e);
            }
        };

        checkStatus(); // Check immediately
        const interval = setInterval(checkStatus, 10000); // Then every 10s

        return () => clearInterval(interval);
    }, [pollingWithdrawal, pendingWithdrawalId, vaultContract]);

    const handleForwardToVault = async () => {
        try {
            setLoading(true);
            const resp = await fetch(`${BACKEND_URL}/api/withdrawal/forward-to-vault`, {
                method: "POST"
            });
            const data = await resp.json();
            if (data.status === "success") {
                showToast({
                    type: "success",
                    title: "Funds Forwarded!",
                    message: `$${data.amount} sent to vault`,
                    txHash: data.tx_hash
                });
                const res = await fetch(`${BACKEND_URL}/api/withdrawal/status`);
                const statusData = await res.json();
                setWithdrawalStatus(statusData);
            } else {
                showToast({ type: "error", title: "Forward Failed", message: data.message });
            }
        } catch (e) {
            console.error(e);
            showToast({ type: "error", title: "Failed to forward funds" });
        } finally {
            setLoading(false);
        }
    };

    // V2 Queue-based withdrawal completion
    const [withdrawRequestId, setWithdrawRequestId] = useState<string>("0");

    const handleCompleteWithdrawal = async () => {
        if (!vaultContract || !address || !account) return;

        try {
            setLoading(true);
            setWithdrawMessage("Preparing complete_withdraw...");

            const requestId = parseInt(withdrawRequestId || "0");

            // 1. Get the withdrawal request to find USDC value
            const withdrawal = await vaultContract.call("get_pending_withdrawal", [cairo.uint256(requestId)]) as any;

            // starknet.js combines u256 automatically, so struct is:
            // [0]=user, [1]=shares, [2]=min_assets, [3]=usdc_value, [4]=timestamp, [5]=status
            const usdcValue = BigInt(withdrawal[3] || 0);
            console.log("Withdrawal data:", withdrawal);
            console.log("USDC value:", usdcValue.toString());

            if (usdcValue === BigInt(0)) {
                throw new Error("Withdrawal not marked as ready yet. Contact operator to mark_withdrawal_ready first.");
            }

            setWithdrawMessage("Getting swap quote from AVNU...");

            console.log("Calling AVNU with:", {
                sellToken: CONTRACTS.USDC,
                buyToken: CONTRACTS.WBTC,
                amount: usdcValue.toString(),
                takerAddress: CONTRACTS.VAULT
            });

            // 2. Get AVNU swap calldata (USDC -> wBTC)
            const swapData = await getSwapCalldata(
                CONTRACTS.USDC,
                CONTRACTS.WBTC,
                usdcValue,
                CONTRACTS.VAULT // The vault performs the swap
            );

            console.log("AVNU response:", swapData);

            if (!swapData) {
                throw new Error(`Failed to get swap quote from AVNU for ${usdcValue.toString()} USDC. Check console for details.`);
            }

            const swapCall = swapData.calldata.calls.find(
                (c: any) => c.entrypoint === "multi_route_swap"
            );

            if (!swapCall) {
                throw new Error("Invalid AVNU response");
            }

            setWithdrawMessage("Submitting complete_withdraw transaction...");

            // 3. Execute complete_withdraw on vault
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
            showToast({
                type: "success",
                title: "Withdrawal Submitted!",
                message: "Transaction is being processed",
                txHash: result.transaction_hash
            });

            // Refresh balance
            setTimeout(loadPosition, 5000);

        } catch (err: any) {
            console.error("Complete withdrawal error:", err);
            showToast({ type: "error", title: "Withdrawal Failed", message: err.message });
        } finally {
            setLoading(false);
            setWithdrawMessage("");
        }
    };

    const formatUsdc = (raw: bigint) => {
        return (Number(raw) / 1e6).toFixed(2);
    };

    const formatShares = (raw: bigint) => {
        return (Number(raw) / 1e6).toFixed(6);
    };

    if (!address) {
        return (
            <div className="text-center py-12">
                <p className="text-muted text-lg">Connect your wallet to view your position</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="text-center py-12">
                <p className="text-muted text-lg">Loading position...</p>
            </div>
        );
    }

    if (shares === BigInt(0) && userWithdrawals.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-muted text-lg mb-4">You don&apos;t have any shares in the vault</p>
                <a href="/open-position" className="btn-primary inline-block">
                    Deposit
                </a>
            </div>
        );
    }

    // Show link to withdrawals page if user has no shares but has pending withdrawals
    if (shares === BigInt(0) && userWithdrawals.length > 0) {
        return (
            <div className="max-w-xl mx-auto space-y-6 text-center py-12">
                <p className="text-muted mb-4">Your shares are locked in pending withdrawals</p>
                <div className="flex gap-4 justify-center">
                    <a href="/withdrawals" className="btn-primary inline-block">
                        View Withdrawals
                    </a>
                    <a href="/open-position" className="btn-secondary inline-block">
                        Make New Deposit
                    </a>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-lg mx-auto">
            <h1 className="text-2xl font-bold mb-8">Your Position</h1>

            {/* Position Stats */}
            <div className="card mb-6">
                <div className="flex justify-between mb-4">
                    <span className="text-muted">Vault Shares</span>
                    <span className="font-data text-highlight text-xl">
                        {formatShares(shares)}
                    </span>
                </div>
                <div className="flex justify-between mb-4">
                    <span className="text-muted">Share Value</span>
                    <span className="font-data text-xl">
                        ${formatUsdc(shareValue)} USDC
                    </span>
                </div>
                <div className="flex justify-between border-t border-[#2a2a2a] pt-4">
                    <span className="text-muted">Vault Total</span>
                    <span className="font-data text-xl">${formatUsdc(totalUsdc)} USDC</span>
                </div>
            </div>

            {/* Backend Status */}
            {vaultStatus && (
                <div className="card mb-6">
                    <h3 className="text-white font-medium mb-4">Strategy Status</h3>

                    {/* Delta Status Badge */}
                    <div className="mb-4">
                        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${vaultStatus.delta_status === "NEUTRAL"
                            ? "bg-green-500/20 text-green-400"
                            : vaultStatus.delta_status === "LONG_HEAVY"
                                ? "bg-yellow-500/20 text-yellow-400"
                                : "bg-red-500/20 text-red-400"
                            }`}>
                            <span className={`w-2 h-2 rounded-full ${vaultStatus.delta_status === "NEUTRAL" ? "bg-green-400" :
                                vaultStatus.delta_status === "LONG_HEAVY" ? "bg-yellow-400" : "bg-red-400"
                                }`}></span>
                            Delta: {vaultStatus.delta_status || "UNKNOWN"} ({((vaultStatus.delta || 0) * 100).toFixed(2)}%)
                        </div>
                    </div>

                    <div className="flex justify-between mb-2">
                        <span className="text-muted">wBTC Held (LONG)</span>
                        <span className="text-highlight">{(vaultStatus.wbtc_held || 0).toFixed(6)} BTC</span>
                    </div>
                    <div className="flex justify-between mb-2">
                        <span className="text-muted">Total NAV</span>
                        <span className="text-white">${(vaultStatus.total_nav || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between mb-2">
                        <span className="text-muted">Funding Rate</span>
                        <span className="text-green-400">{vaultStatus.funding_rate_percent}</span>
                    </div>
                    <div className="flex justify-between mb-2">
                        <span className="text-muted">Position</span>
                        <span className={vaultStatus.has_position ? "text-highlight" : "text-muted"}>
                            {vaultStatus.has_position ? "Active Short" : "Idle"}
                        </span>
                    </div>
                    <div className="flex justify-between mb-2">
                        <span className="text-muted">Est. APY</span>
                        <span className="text-green-400">{vaultStatus.estimated_apy.toFixed(1)}%</span>
                    </div>
                </div>
            )}

            {/* Withdrawal Section */}
            <div className="card mb-6">
                <h3 className="text-white font-medium mb-4">Withdraw</h3>

                {withdrawalStatus && (
                    <div className="mb-6 py-3 px-4 bg-[#1a1a1a] rounded-lg text-sm">
                        <div className="flex justify-between mb-2">
                            <span className="text-muted">Free Liquidity</span>
                            <span className="text-highlight">${withdrawalStatus.extended_available.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between mb-2">
                            <span className="text-muted">Operator Wallet</span>
                            <span>${withdrawalStatus.operator_balance.toFixed(2)}</span>
                        </div>
                        {withdrawalStatus.operator_balance > 0.1 && (
                            <button
                                onClick={handleForwardToVault}
                                disabled={loading}
                                className="mt-2 w-full py-2 bg-highlight/20 hover:bg-highlight/30 border border-highlight/50 text-highlight text-xs rounded transition-colors"
                            >
                                {loading ? "Forwarding..." : "Forward to Vault ↓"}
                            </button>
                        )}
                        {withdrawalStatus.has_positions && (
                            <p className="text-yellow-500 text-xs mt-2 flex items-center gap-1">
                                <span>⚠️</span> Part of your position will be closed automatically
                            </p>
                        )}
                    </div>
                )}

                <div className="space-y-4 mb-6">
                    <div>
                        <label className="block text-xs text-muted mb-1 ml-1">Shares to Burn</label>
                        <div className="relative">
                            <input
                                type="number"
                                value={withdrawAmountShares}
                                onChange={(e) => setWithdrawAmountShares(e.target.value)}
                                className="w-full bg-[#121212] border border-[#2a2a2a] rounded-lg py-3 px-4 font-data text-white outline-none focus:border-highlight transition-colors"
                            />
                            <button
                                onClick={() => setWithdrawAmountShares((Number(shares) / 1e6).toString())}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] bg-[#2a2a2a] px-2 py-1 rounded text-muted hover:text-white transition-colors"
                            >
                                MAX
                            </button>
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs text-muted mb-1 ml-1">Recipient Address (wBTC)</label>
                        <input
                            type="text"
                            value={recipientAddress}
                            onChange={(e) => setRecipientAddress(e.target.value)}
                            placeholder="Starknet address"
                            className="w-full bg-[#121212] border border-[#2a2a2a] rounded-lg py-3 px-4 font-data text-sm text-white outline-none focus:border-highlight transition-colors"
                        />
                    </div>
                </div>

                {/* Single Withdrawal Button - State-based */}
                {pendingWithdrawalId === null || pendingWithdrawalStatus === 3 || pendingWithdrawalStatus === 4 ? (
                    // No pending withdrawal - show Request button
                    <button
                        onClick={requestWithdrawal}
                        disabled={withdrawing || loading || shares === BigInt(0)}
                        className="btn-primary w-full py-4 font-bold tracking-wide"
                    >
                        {withdrawing ? (
                            <span className="flex items-center justify-center gap-2">
                                <span className="w-4 h-4 border-2 border-highlight border-t-transparent rounded-full animate-spin"></span>
                                Requesting...
                            </span>
                        ) : "Withdraw"}
                    </button>
                ) : pendingWithdrawalStatus === 0 || pendingWithdrawalStatus === 1 ? (
                    // Pending or Processing - show waiting state
                    <div className="w-full py-4 bg-yellow-600/20 border border-yellow-500/50 text-yellow-400 font-bold rounded-xl flex flex-col items-center justify-center gap-2">
                        <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin"></span>
                            Processing Withdrawal...
                        </span>
                        <span className="text-xs opacity-70">Request #{pendingWithdrawalId} - Waiting for operator</span>
                    </div>
                ) : pendingWithdrawalStatus === 2 ? (
                    // Ready - show Complete button
                    <button
                        onClick={handleCompleteWithdrawal}
                        disabled={loading || withdrawing}
                        className="w-full py-4 bg-green-600 hover:bg-green-500 text-white font-bold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex flex-col items-center justify-center gap-1 shadow-lg shadow-green-900/20"
                    >
                        <span className="text-sm">Complete Withdrawal</span>
                        <span className="text-[10px] opacity-80 uppercase tracking-widest">Swap USDC → wBTC</span>
                    </button>
                ) : null}

                <p className="text-muted text-[10px] mt-4 text-center leading-relaxed">
                    Withdrawals are processed in two steps: first from Extended to Unbound,
                    then Unbound to your wallet. Total time: ~5-15 minutes.
                </p>
            </div>

            {/* Info */}
            <div className="text-muted text-sm p-4 bg-[#1a1a1a] rounded-lg">
                <p>
                    Your USDC is earning yield through the funding rate arbitrage strategy on Extended.
                </p>
            </div>

            {/* Link to Withdrawals page if there are pending withdrawals */}
            {userWithdrawals.length > 0 && (
                <div className="text-center p-4 bg-[#1a1a1a] rounded-lg">
                    <a href="/withdrawals" className="text-highlight hover:text-white transition-colors">
                        You have {userWithdrawals.length} pending withdrawal{userWithdrawals.length > 1 ? 's' : ''} →
                    </a>
                </div>
            )}
        </div>
    );
}
