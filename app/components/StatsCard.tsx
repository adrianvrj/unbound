"use client";

import { SlotNumber } from "./AnimatedNumber";

interface StatsCardProps {
    label: string;
    value: string;
}

export function StatsCard({ label, value }: StatsCardProps) {
    return (
        <div>
            <p className="text-muted text-sm mb-3 font-ui">{label}</p>
            <div className="font-data text-5xl lg:text-6xl text-highlight tracking-tight">
                <SlotNumber value={value} duration={1200} />
            </div>
        </div>
    );
}
