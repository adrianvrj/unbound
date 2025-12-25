"use client";

import { useEffect, useState } from "react";
import { StatsCard } from "@/components/StatsCard";
import { getVaultStatus, getAPYData, VaultStatus, APYData } from "@/lib/backend-api";

export default function VaultPage() {
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [apyData, setApyData] = useState<APYData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [leverage, setLeverage] = useState(2);

  // Calculate APY based on selected leverage
  const calculatedApy = apyData
    ? (apyData.current_funding_rate * 24 * 365 * leverage * 100).toFixed(1)
    : "0";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusData, apy] = await Promise.all([
          getVaultStatus(),
          getAPYData()
        ]);

        if (statusData) setStatus(statusData);
        if (apy) setApyData(apy);

        if (!statusData && !apy) {
          setError("Backend not available");
        }
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to connect to backend");
      }
      setLoading(false);
    };

    fetchData();

    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatUsd = (value: number): string => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(2)}k`;
    return value.toFixed(2);
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-muted text-lg">Loading vault data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400 text-lg mb-4">{error}</p>
        <p className="text-muted text-sm">
          Start the backend: <code className="bg-[#2a2a2a] px-2 py-1 rounded">cd backend && python main.py</code>
        </p>
      </div>
    );
  }

  return (
    <div className="relative mb-14">
      {/* Stats */}
      <div className="relative z-10 max-w-lg pt-8">
        <div className="space-y-12">
          {/* Delta Status Indicator */}
          {/* <div className="mb-6">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${status?.delta_status === "NEUTRAL"
                ? "bg-green-500/20 text-green-400"
                : status?.delta_status === "LONG_HEAVY"
                  ? "bg-yellow-500/20 text-yellow-400"
                  : "bg-red-500/20 text-red-400"
              }`}>
              <span className={`w-2 h-2 rounded-full ${status?.delta_status === "NEUTRAL" ? "bg-green-400" :
                  status?.delta_status === "LONG_HEAVY" ? "bg-yellow-400" : "bg-red-400"
                }`}></span>
              Delta: {status?.delta_status || "UNKNOWN"}
              <span className="text-muted">({((status?.delta || 0) * 100).toFixed(2)}%)</span>
            </div>
          </div> */}

          {/* Total NAV (wBTC value + Extended equity) */}
          <StatsCard
            label="Total NAV"
            value={`$${formatUsd(status?.total_nav || 0)}`}
          />

          {/* wBTC Held (LONG exposure) */}
          <StatsCard
            label="wBTC Held (LONG)"
            value={`${(status?.wbtc_held || 0).toFixed(6)} BTC`}
          />

          {/* Funding Rate */}
          <StatsCard
            label="Current Funding Rate"
            value={status?.funding_rate_percent || "0%"}
          />

          {/* APY Section with Leverage Selector */}
          <div>
            {/* Leverage Selector */}
            <div className="mb-4">
              <label className="text-muted text-sm mb-2 block font-ui">Leverage</label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="0.5"
                  value={leverage}
                  onChange={(e) => setLeverage(parseFloat(e.target.value))}
                  className="flex-1 h-2 bg-[#2a2a2a] rounded-lg appearance-none cursor-pointer accent-highlight"
                />
                <span className="text-white font-mono text-lg w-12 text-right">{leverage}x</span>
              </div>
            </div>

            {/* APY Display with Tooltip */}
            <div className="relative group">
              <StatsCard
                label={`Estimated APY (${leverage}x)`}
                value={`${calculatedApy}%`}
              />
              {/* Info icon */}
              <div className="absolute top-0 right-0 mt-1 mr-1">
                <span className="text-muted text-xs cursor-help hover:text-white transition-colors">ⓘ</span>
                {/* Tooltip */}
                <div className="absolute right-0 top-6 w-64 p-3 bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                  <p className="text-xs text-gray-300 leading-relaxed">
                    APY is variable and based on the funding rate that shorts receive from longs.
                  </p>
                  <p className="text-xs text-highlight mt-2 font-medium">
                    30-day avg: ~{(14 * leverage / 2).toFixed(0)}%
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
