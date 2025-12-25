"use client";

import { useEffect, useRef } from "react";

interface BTCChartProps {
    height?: number;
}

export default function BTCChart({ height = 400 }: BTCChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Clear any existing widget
        containerRef.current.innerHTML = "";

        // Create container div for widget
        const widgetContainer = document.createElement("div");
        widgetContainer.className = "tradingview-widget-container__widget";
        widgetContainer.style.height = `calc(${height}px - 32px)`;
        widgetContainer.style.width = "100%";
        containerRef.current.appendChild(widgetContainer);

        // Create the TradingView Advanced Chart widget script
        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
        script.async = true;
        script.innerHTML = JSON.stringify({
            autosize: true,
            symbol: "COINBASE:BTCUSD",
            interval: "15",
            timezone: "Etc/UTC",
            theme: "dark",
            style: "1",
            locale: "en",
            allow_symbol_change: false,
            hide_top_toolbar: false,
            hide_legend: true,
            save_image: false,
            calendar: false,
            hide_volume: true,
            support_host: "https://www.tradingview.com",
            backgroundColor: "rgba(0, 0, 0, 0)",
            gridColor: "rgba(66, 66, 66, 0.3)",
        });

        containerRef.current.appendChild(script);

        return () => {
            if (containerRef.current) {
                containerRef.current.innerHTML = "";
            }
        };
    }, [height]);

    return (
        <div
            ref={containerRef}
            className="tradingview-widget-container rounded-lg overflow-hidden"
            style={{ height: `${height}px`, width: "100%" }}
        />
    );
}
