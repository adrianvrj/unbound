"use client";

import { useState, useEffect } from "react";
import { useAccount, useContract } from "@starknet-react/core";
import { cairo, CallData } from "starknet";
import { CONTRACTS, ERC20_ABI } from "@/lib/contracts";
import { getSwapCalldata, getQuote } from "@/lib/avnu";
import { getAPYData, APYData } from "@/lib/backend-api";
import { useToast } from "@/components/Toast";
import Image from "next/image";

const FUNDING_VAULT = CONTRACTS.VAULT;

const FUNDING_VAULT_ABI = [
    {
        name: "deposit",
        type: "function",
        inputs: [
            { name: "assets", type: "core::integer::u256" },
            { name: "receiver", type: "core::starknet::contract_address::ContractAddress" },
            { name: "avnu_calldata", type: "core::array::Array::<core::felt252>" }
        ],
        outputs: [{ type: "core::integer::u256" }],
        state_mutability: "external"
    }
];

export default function DepositPage() {
    const { address, account } = useAccount();
    const [depositAmount, setDepositAmount] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const { showToast } = useToast();
    const [apyData, setApyData] = useState<APYData | null>(null);

    const [wbtcBalance, setWbtcBalance] = useState<string | null>(null);
    const [wbtcPrice, setWbtcPrice] = useState(95000);
    const [usdcEstimate, setUsdcEstimate] = useState<number | null>(null);
    const [loadingQuote, setLoadingQuote] = useState(false);

    const { contract: wbtcContract } = useContract({
        abi: ERC20_ABI as any,
        address: CONTRACTS.WBTC as any,
    });

    useEffect(() => {
        const fetchAPY = async () => {
            const data = await getAPYData();
            if (data) setApyData(data);
        };
        fetchAPY();
    }, []);

    useEffect(() => {
        const fetchBalance = async () => {
            if (!wbtcContract || !address) {
                setWbtcBalance(null);
                return;
            }
            try {
                const balance = await wbtcContract.balance_of(address);
                const formatted = (Number(balance) / 1e8).toFixed(8);
                setWbtcBalance(formatted);
            } catch {
                setWbtcBalance(null);
            }
        };
        fetchBalance();
    }, [wbtcContract, address]);

    useEffect(() => {
        const fetchQuote = async () => {
            const amount = parseFloat(depositAmount);
            if (!amount || amount <= 0) {
                setUsdcEstimate(null);
                return;
            }

            setLoadingQuote(true);
            try {
                const wbtcAmount = BigInt(Math.round(amount * 1e8));
                // Delta-neutral: only 50% gets swapped, other 50% kept as wBTC
                const wbtcToSwap = wbtcAmount / BigInt(2);

                const quote = await getQuote(
                    CONTRACTS.WBTC,
                    CONTRACTS.USDC || "0x053b40A647CEDfca6cA84f542A0fe36736031905A9639a7f19A3C1e66bFd5080",
                    wbtcToSwap,  // Only quote for 50%
                    address || "0x0"
                );

                if (quote) {
                    const usdcFromSwap = Number(quote.buyAmount) / 1e6;
                    // Total value ≈ 2x the USDC from swap (since we keep 50% wBTC worth same value)
                    const totalValue = usdcFromSwap * 2;
                    setUsdcEstimate(totalValue);
                    setWbtcPrice(totalValue / amount);
                }
            } catch (err) {
                console.error("Quote error:", err);
            }
            setLoadingQuote(false);
        };

        const debounce = setTimeout(fetchQuote, 500);
        return () => clearTimeout(debounce);
    }, [depositAmount, address]);

    const depositBtc = parseFloat(depositAmount) || 0;
    const depositValueUsd = depositBtc * wbtcPrice;

    const handleDeposit = async () => {
        if (!account || !address) {
            setError("Please connect your wallet");
            return;
        }

        if (depositBtc <= 0) {
            setError("Enter a valid deposit amount");
            return;
        }

        // Minimum deposit: 0.0001 BTC (Extended position size limit)
        if (depositBtc < 0.0001) {
            setError("Minimum deposit is 0.0001 wBTC");
            return;
        }

        setLoading(true);
        setError("");
        setError("");

        try {
            const wbtcAmountRaw = BigInt(Math.round(depositBtc * 1e8));

            // Delta-neutral: only 50% of wBTC gets swapped to USDC
            // The other 50% is kept in vault as LONG exposure
            const wbtcToSwap = wbtcAmountRaw / BigInt(2);

            const swapData = await getSwapCalldata(
                CONTRACTS.WBTC,
                CONTRACTS.USDC || "0x053b40A647CEDfca6cA84f542A0fe36736031905A9639a7f19A3C1e66bFd5080",
                wbtcToSwap,  // Only swap 50%
                FUNDING_VAULT,
                1
            );

            if (!swapData) {
                throw new Error("Failed to get swap calldata from AVNU");
            }

            const swapCall = swapData.calldata.calls.find(
                (c: any) => c.entrypoint === "multi_route_swap"
            );

            if (!swapCall) {
                throw new Error("No multi_route_swap call found in AVNU response");
            }

            const avnuCalldata = swapCall.calldata || [];

            const calls = [
                {
                    contractAddress: CONTRACTS.WBTC,
                    entrypoint: "approve",
                    calldata: CallData.compile({
                        spender: FUNDING_VAULT,
                        amount: cairo.uint256(wbtcAmountRaw)
                    })
                },
                {
                    contractAddress: FUNDING_VAULT,
                    entrypoint: "deposit",
                    calldata: CallData.compile({
                        assets: cairo.uint256(wbtcAmountRaw),
                        receiver: address,
                        min_shares: cairo.uint256(BigInt(0)), // Temporarily 0 for testing - TODO: restore slippage protection
                        avnu_calldata: avnuCalldata
                    })
                }
            ];

            const result = await account.execute(calls);
            showToast({
                type: "success",
                title: "Deposit Submitted!",
                message: "Your position is being created",
                txHash: result.transaction_hash
            });
            setDepositAmount("");

        } catch (err: any) {
            console.error("Deposit error:", err);
            setError(err.message || "Deposit failed");
            showToast({ type: "error", title: "Deposit Failed", message: err.message });
        }

        setLoading(false);
    };

    return (
        <div className="max-w-lg mx-auto">
            {/* Main Card */}
            <div className="bg-card rounded-2xl border border-[#2a2a2a] overflow-hidden">
                {/* Deposit Input Section */}
                <div className="p-6 border-b border-[#2a2a2a]">
                    <label className="text-muted text-xs uppercase tracking-wider block mb-3">
                        You Deposit
                    </label>
                    <div className="flex items-center gap-2 sm:gap-4">
                        <input
                            type="number"
                            value={depositAmount}
                            onChange={(e) => setDepositAmount(e.target.value)}
                            placeholder="0.00"
                            className="flex-1 min-w-0 bg-transparent text-2xl sm:text-4xl font-light text-white outline-none placeholder:text-[#3a3a3a]"
                            step="0.0001"
                            min="0"
                        />
                        <div className="shrink-0 flex items-center gap-1.5 sm:gap-2 bg-[#1a1a1a] px-2 sm:px-4 py-2 rounded-lg">
                            <Image src="/wbtc.svg" alt="wBTC" width={20} height={20} className="sm:w-6 sm:h-6" />
                            <span className="font-medium text-sm sm:text-base">wBTC</span>
                        </div>
                    </div>
                    {wbtcBalance && (
                        <div className="flex items-center justify-between mt-4 text-sm">
                            <span className="text-muted">
                                Balance: {parseFloat(wbtcBalance).toFixed(6)} wBTC
                            </span>
                            <button
                                onClick={() => setDepositAmount(wbtcBalance)}
                                className="text-highlight hover:opacity-80 font-medium"
                            >
                                MAX
                            </button>
                        </div>
                    )}
                </div>

                {/* You Receive Section */}
                <div className="p-6 bg-[#0f0f0f]">
                    <label className="text-muted text-xs uppercase tracking-wider block mb-3">
                        You Receive
                    </label>
                    <p className="text-3xl font-light text-white">
                        {loadingQuote ? (
                            <span className="text-muted">...</span>
                        ) : usdcEstimate ? (
                            <span>${usdcEstimate.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                        ) : (
                            <span className="text-[#3a3a3a]">$0.00</span>
                        )}
                        <span className="text-muted text-sm ml-2">in vault shares</span>
                    </p>
                </div>

                {/* Details */}
                <div className="p-6 space-y-3 text-sm border-t border-[#2a2a2a]">
                    <div className="flex justify-between">
                        <span className="text-muted">Strategy</span>
                        <span className="text-highlight font-medium">Delta-Neutral Short</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-muted">Leverage</span>
                        <span className="text-white">2x</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-muted">Platform</span>
                        <span className="text-white">Extended</span>
                    </div>
                    {apyData && (
                        <div className="flex justify-between pt-3 border-t border-[#2a2a2a]">
                            <span className="text-muted">Estimated APY</span>
                            <span className="text-highlight font-medium">{apyData.configured_apy.toFixed(1)}%</span>
                        </div>
                    )}
                </div>

                {/* Deposit Button */}
                <div className="p-6 pt-0">
                    <button
                        onClick={handleDeposit}
                        disabled={loading || !address || depositBtc <= 0}
                        className="btn-primary w-full py-4 text-lg font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <span className="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin"></span>
                                Processing...
                            </span>
                        ) : !address ? (
                            "Connect Wallet"
                        ) : depositBtc <= 0 ? (
                            "Enter Amount"
                        ) : (
                            "Deposit"
                        )}
                    </button>

                    {error && (
                        <p className="text-red-400 text-sm text-center mt-4">{error}</p>
                    )}
                </div>
            </div>

            {/* How it Works */}
            <div className="mt-8 p-6 bg-[#1a1a1a] rounded-xl border border-[#2a2a2a]">
                <h3 className="text-white font-medium mb-4">How it Works</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                    <div>
                        <div className="w-8 h-8 sm:w-10 sm:h-10 mx-auto mb-2 rounded-full bg-highlight/10 text-highlight flex items-center justify-center font-bold text-sm sm:text-base">1</div>
                        <p className="text-[10px] sm:text-xs text-muted">Swap wBTC to USDC</p>
                    </div>
                    <div>
                        <div className="w-8 h-8 sm:w-10 sm:h-10 mx-auto mb-2 rounded-full bg-highlight/10 text-highlight flex items-center justify-center font-bold text-sm sm:text-base">2</div>
                        <p className="text-[10px] sm:text-xs text-muted">Deposit to Extended</p>
                    </div>
                    <div>
                        <div className="w-8 h-8 sm:w-10 sm:h-10 mx-auto mb-2 rounded-full bg-highlight/10 text-highlight flex items-center justify-center font-bold text-sm sm:text-base">3</div>
                        <p className="text-[10px] sm:text-xs text-muted">Open short position</p>
                    </div>
                    <div>
                        <div className="w-8 h-8 sm:w-10 sm:h-10 mx-auto mb-2 rounded-full bg-highlight/10 text-highlight flex items-center justify-center font-bold text-sm sm:text-base">4</div>
                        <p className="text-[10px] sm:text-xs text-muted">Earn funding</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
