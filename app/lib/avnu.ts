
// AVNU Mainnet API base URL
const AVNU_BASE_URL = "https://starknet.api.avnu.fi";

export interface QuoteResponse {
    quoteId: string;
    sellTokenAddress: string;
    sellAmount: string;
    buyTokenAddress: string;
    buyAmount: string;
    routes: any[];
}

export interface BuildResponse {
    chainId: string;
    calls: Array<{
        contractAddress: string;
        entrypoint: string;
        calldata: string[];
    }>;
}

/**
 * Get a quote from AVNU API
 */
export async function getQuote(
    sellToken: string,
    buyToken: string,
    sellAmount: bigint,
    takerAddress: string
): Promise<QuoteResponse | null> {
    try {
        const sellAmountHex = "0x" + sellAmount.toString(16);

        const response = await fetch(
            `${AVNU_BASE_URL}/swap/v2/quotes?sellTokenAddress=${sellToken}&buyTokenAddress=${buyToken}&sellAmount=${sellAmountHex}&takerAddress=${takerAddress}`
        );

        if (!response.ok) {
            throw new Error(`AVNU API error: ${response.status} - ${await response.text()}`);
        }

        const quotes = await response.json();

        if (!quotes || quotes.length === 0) {
            console.warn("No quotes found from AVNU");
            return null;
        }

        return quotes[0];
    } catch (error) {
        console.error("Error fetching AVNU quote:", error);
        return null;
    }
}

/**
 * Build swap transaction calldata using AVNU build endpoint
 * Returns the raw calldata array to pass to the contract
 */
export async function buildSwapCalldata(
    quoteId: string,
    takerAddress: string,
    slippage: number = 0.01  // 1% default slippage
): Promise<BuildResponse | null> {
    try {
        const response = await fetch(`${AVNU_BASE_URL}/swap/v2/build`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                quoteId: quoteId,
                takerAddress: takerAddress,
                slippage: slippage,
                includeApprove: true,
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`AVNU build error: ${response.status} - ${errorText}`);
        }

        const buildResult: BuildResponse = await response.json();

        if (!buildResult.calls || buildResult.calls.length === 0) {
            console.error("No calls in AVNU build response");
            return null;
        }

        // Get the calldata from the first call (the swap)
        const swapCall = buildResult;

        return swapCall;
    } catch (error) {
        console.error("Error building AVNU swap:", error);
        return null;
    }
}

/**
 * Complete flow: get quote and build calldata for swap
 */
export async function getSwapCalldata(
    sellToken: string,
    buyToken: string,
    sellAmount: bigint,
    takerAddress: string,
    slippage: number = 0.01
): Promise<{ calldata: BuildResponse; buyAmount: bigint } | null> {
    const quote = await getQuote(sellToken, buyToken, sellAmount, takerAddress);
    if (!quote) {
        console.error("Failed at step 1: getQuote returned null");
        return null;
    }
    const calldata = await buildSwapCalldata(quote.quoteId, takerAddress, slippage);
    if (!calldata) {
        console.error("Failed at step 2: buildSwapCalldata returned null");
        return null;
    }

    return {
        calldata,
        buyAmount: BigInt(quote.buyAmount),
    };
}

// Calculate minimum output with slippage
export function calculateMinOutput(amount: bigint, slippageBps: number): bigint {
    return (amount * BigInt(10000 - slippageBps)) / BigInt(10000);
}
