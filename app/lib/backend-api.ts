/**
 * Backend API client for the Funding Rate Vault
 * Connects to the Python backend running on port 8001
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";

// ============ Types ============

export interface VaultStatus {
    status: string;
    funding_rate: number;
    funding_rate_percent: string;
    estimated_apy: number;
    has_position: boolean;
    position_size: number;
    position_value: number;
    unrealized_pnl: number;
    balance: number;
    equity: number;
    leverage: number;
    market: string;
    timestamp: string;
    // Delta-neutral fields
    wbtc_held: number;
    wbtc_value_usd: number;
    total_nav: number;
    delta: number;
    delta_status: string;  // "NEUTRAL", "LONG_HEAVY", "SHORT_HEAVY"
}

export interface APYData {
    current_funding_rate: number;
    hourly_rate_percent: string;
    daily_rate_percent: string;
    estimated_apy_1x: number;
    estimated_apy_2x: number;
    estimated_apy_5x: number;
    configured_leverage: number;
    configured_apy: number;
}

export interface Position {
    has_position: boolean;
    side: string | null;
    size: number;
    value: number;
    open_price: number;
    mark_price: number;
    liquidation_price: number;
    unrealized_pnl: number;
    leverage: number;
}

export interface FundingPayment {
    market: string;
    side: string;
    size: number;
    funding_fee: number;
    funding_rate: number;
    paid_time: number;
    paid_time_formatted: string;
}

export interface RebalancerStatus {
    running: boolean;
    iteration_count: number;
    last_run: string | null;
    last_action: Record<string, any> | null;
    interval_seconds: number;
    market: string;
    leverage: number;
}

// ============ API Functions ============

async function fetchAPI<T>(endpoint: string): Promise<T | null> {
    try {
        const response = await fetch(`${BACKEND_URL}${endpoint}`);
        if (!response.ok) {
            console.error(`API error: ${response.status}`);
            return null;
        }
        return response.json();
    } catch (error) {
        console.error(`Failed to fetch ${endpoint}:`, error);
        return null;
    }
}

async function postAPI<T>(endpoint: string): Promise<T | null> {
    try {
        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            method: "POST",
        });
        if (!response.ok) {
            console.error(`API error: ${response.status}`);
            return null;
        }
        return response.json();
    } catch (error) {
        console.error(`Failed to POST ${endpoint}:`, error);
        return null;
    }
}

/**
 * Get current vault status
 */
export async function getVaultStatus(): Promise<VaultStatus | null> {
    return fetchAPI<VaultStatus>("/api/status");
}

/**
 * Get APY estimates
 */
export async function getAPYData(): Promise<APYData | null> {
    return fetchAPI<APYData>("/api/apy");
}

/**
 * Get current position
 */
export async function getPosition(): Promise<Position | null> {
    return fetchAPI<Position>("/api/position");
}

/**
 * Get funding payment history
 */
export async function getFundingHistory(limit: number = 50): Promise<FundingPayment[] | null> {
    return fetchAPI<FundingPayment[]>(`/api/funding-history?limit=${limit}`);
}

/**
 * Get rebalancer status
 */
export async function getRebalancerStatus(): Promise<RebalancerStatus | null> {
    return fetchAPI<RebalancerStatus>("/api/rebalancer/status");
}

/**
 * Start the rebalancer
 */
export async function startRebalancer(): Promise<{ status: string } | null> {
    return postAPI<{ status: string }>("/api/rebalancer/start");
}

/**
 * Stop the rebalancer
 */
export async function stopRebalancer(): Promise<{ status: string } | null> {
    return postAPI<{ status: string }>("/api/rebalancer/stop");
}

/**
 * Run rebalancer once
 */
export async function runRebalancerOnce(): Promise<{ status: string; result: any } | null> {
    return postAPI<{ status: string; result: any }>("/api/rebalancer/run-once");
}

// ============ V2 Queue Functions ============

export interface V2ServiceStatus {
    running: boolean;
    last_processed_id?: number;
    pending_count: number;
    processing_count?: number;
    processing_interval?: number;
}

export interface V2Status {
    queue_services_enabled: boolean;
    services: {
        deposit_processor?: V2ServiceStatus;
        withdrawal_processor?: V2ServiceStatus & {
            processing_details: Record<string, { usdc_value: number; step: string }>;
        };
        position_manager?: {
            running: boolean;
            position_closed_due_to_funding: boolean;
            last_rebalance: string | null;
            position: {
                size: number;
                entry_price: number;
                mark_price: number;
                margin_ratio: number;
                unrealized_pnl: number;
                funding_rate: number;
                is_healthy: boolean;
            } | null;
        };
        nav_reporter?: {
            running: boolean;
            last_update: string | null;
            last_nav: number;
            current_equity: number;
            update_interval: number;
            next_update_in: number;
        };
    };
}

export interface DepositQueueItem {
    request_id: number;
    user: string;
    receiver: string;
    usdc_amount: number;
    min_shares: number;
    timestamp: number;
    processed: boolean;
}

export interface WithdrawalQueueItem {
    request_id: number;
    user: string;
    shares: number;
    min_assets: number;
    usdc_value: number;
    timestamp: number;
    status: number; // 0=Pending, 1=Processing, 2=Ready, 3=Completed, 4=Cancelled
}

export const WITHDRAWAL_STATUS_NAMES: Record<number, string> = {
    0: "Pending",
    1: "Processing",
    2: "Ready",
    3: "Completed",
    4: "Cancelled",
};

/**
 * Get V2 services status
 */
export async function getV2Status(): Promise<V2Status | null> {
    return fetchAPI<V2Status>("/api/queues/status");
}

/**
 * Get V2 queue status
 */
export async function getV2Queues(): Promise<{
    deposits: V2ServiceStatus | null;
    withdrawals: V2ServiceStatus | null;
} | null> {
    return fetchAPI<{ deposits: V2ServiceStatus | null; withdrawals: V2ServiceStatus | null }>("/api/queues");
}
