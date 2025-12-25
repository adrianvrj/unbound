"use client";

import { useEffect, useState, useRef } from "react";

interface SlotNumberProps {
    value: string;
    duration?: number;
    className?: string;
}

export function SlotNumber({ value, duration = 1500, className = "" }: SlotNumberProps) {
    const [displayChars, setDisplayChars] = useState<string[]>([]);
    const [finalizedIndexes, setFinalizedIndexes] = useState<Set<number>>(new Set());
    const intervalRefs = useRef<NodeJS.Timeout[]>([]);

    useEffect(() => {
        // Cleanup previous intervals
        intervalRefs.current.forEach(clearInterval);
        intervalRefs.current = [];

        if (!value) {
            setDisplayChars([]);
            setFinalizedIndexes(new Set());
            return;
        }

        const chars = value.split("");
        const totalChars = chars.length;

        // Initialize with random chars (only for digits)
        setDisplayChars(chars.map(char => isDigit(char) ? randomDigit() : char));
        setFinalizedIndexes(new Set());

        // Each digit spins and stops one by one (left to right)
        chars.forEach((finalChar, index) => {
            if (!isDigit(finalChar)) {
                // Non-digits (., %, k, M) finalize immediately
                setFinalizedIndexes(prev => new Set([...prev, index]));
                return;
            }

            // Spin interval for this digit
            const spinInterval = setInterval(() => {
                setDisplayChars(prev => {
                    const newChars = [...prev];
                    newChars[index] = randomDigit();
                    return newChars;
                });
            }, 50); // Fast spin

            intervalRefs.current.push(spinInterval);

            // Stop spinning at staggered times (earlier digits stop first)
            const stopDelay = (duration / totalChars) * (index + 1);

            setTimeout(() => {
                clearInterval(spinInterval);
                setDisplayChars(prev => {
                    const newChars = [...prev];
                    newChars[index] = finalChar;
                    return newChars;
                });
                setFinalizedIndexes(prev => new Set([...prev, index]));
            }, stopDelay);
        });

        return () => {
            intervalRefs.current.forEach(clearInterval);
        };
    }, [value, duration]);

    const isDigit = (char: string) => /[0-9]/.test(char);
    const randomDigit = () => Math.floor(Math.random() * 10).toString();

    return (
        <span className={className}>
            {displayChars.map((char, i) => (
                <span
                    key={i}
                    className={`inline-block transition-opacity duration-200 ${finalizedIndexes.has(i) ? "opacity-100" : "opacity-70"
                        }`}
                    style={{
                        animation: !finalizedIndexes.has(i) && isDigit(value[i])
                            ? "none"
                            : "none"
                    }}
                >
                    {char}
                </span>
            ))}
        </span>
    );
}

// Alternative simpler version with vertical scroll effect
export function SlotNumberVertical({ value, duration = 1200, className = "" }: SlotNumberProps) {
    const [displayValue, setDisplayValue] = useState(value);
    const [isSpinning, setIsSpinning] = useState(true);

    useEffect(() => {
        if (!value) {
            setDisplayValue("");
            setIsSpinning(false);
            return;
        }

        setIsSpinning(true);
        const chars = value.split("");
        const totalChars = chars.length;

        // Generate random display during spin
        const spinInterval = setInterval(() => {
            setDisplayValue(
                chars.map(char =>
                    /[0-9]/.test(char) ? Math.floor(Math.random() * 10).toString() : char
                ).join("")
            );
        }, 40);

        // Stop and show final value
        setTimeout(() => {
            clearInterval(spinInterval);
            setDisplayValue(value);
            setIsSpinning(false);
        }, duration);

        return () => clearInterval(spinInterval);
    }, [value, duration]);

    return (
        <span className={`${className} ${isSpinning ? "blur-[1px]" : ""} transition-all duration-200`}>
            {displayValue}
        </span>
    );
}
