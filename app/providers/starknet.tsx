"use client";

import { mainnet } from "@starknet-react/chains";
import { StarknetConfig, jsonRpcProvider, argent, braavos } from "@starknet-react/core";
import { ReactNode } from "react";

const chains = [mainnet];
const connectors = [argent(), braavos()];

function rpc() {
    return {
        nodeUrl: "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_10/dql5pMT88iueZWl7L0yzT56uVk0EBU4L"
    };
}

interface StarknetProviderProps {
    children: ReactNode;
}

export function StarknetProvider({ children }: StarknetProviderProps) {
    return (
        <StarknetConfig
            chains={chains}
            provider={jsonRpcProvider({ rpc })}
            connectors={connectors}
        >
            {children}
        </StarknetConfig>
    );
}
