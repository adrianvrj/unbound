"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAccount, useConnect, useDisconnect } from "@starknet-react/core";

const navItems = [
    { name: "Vault", href: "/" },
    { name: "Open Position", href: "/open-position" },
    { name: "Your Position", href: "/your-position" },
    { name: "Withdrawals", href: "/withdrawals" },
];

export function Header() {
    const pathname = usePathname();
    const { address, status } = useAccount();
    const { connect, connectors } = useConnect();
    const { disconnect } = useDisconnect();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [walletMenuOpen, setWalletMenuOpen] = useState(false);
    const walletMenuRef = useRef<HTMLDivElement>(null);

    const isConnected = status === "connected";

    // Close wallet menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (walletMenuRef.current && !walletMenuRef.current.contains(event.target as Node)) {
                setWalletMenuOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <header className="relative">
            <div className="flex items-center justify-between px-4 sm:px-8 lg:px-12 py-4 sm:py-6">
                {/* Logo */}
                <Link href="/" className="flex items-center">
                    <Image src="/logo.png" alt="Unbound" width={32} height={32} className="sm:w-9 sm:h-9" />
                </Link>

                {/* Desktop Navigation */}
                <nav className="hidden md:flex items-center gap-6 lg:gap-10">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href ||
                            (item.href === "/" && pathname === "/vault");
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`text-sm font-ui transition-colors ${isActive
                                    ? "text-highlight"
                                    : "text-muted hover:text-white"
                                    }`}
                            >
                                {item.name}
                            </Link>
                        );
                    })}
                </nav>

                {/* Right side: Connect + Hamburger */}
                <div className="flex items-center gap-3">
                    {/* Connect Button with Dropdown */}
                    {isConnected ? (
                        <div className="relative" ref={walletMenuRef}>
                            <button
                                onClick={() => setWalletMenuOpen(!walletMenuOpen)}
                                className="btn-primary text-xs sm:text-sm px-3 sm:px-6 py-2"
                            >
                                {address?.slice(0, 4)}...{address?.slice(-4)}
                            </button>

                            {/* Dropdown Menu */}
                            {walletMenuOpen && (
                                <div className="absolute right-0 mt-2 w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg shadow-xl z-50 overflow-hidden">
                                    <button
                                        onClick={() => {
                                            disconnect();
                                            setWalletMenuOpen(false);
                                        }}
                                        className="w-full px-3 sm:px-6 py-2 text-xs sm:text-sm text-center text-gray-300 hover:text-white hover:bg-[#252525] transition-colors"
                                    >
                                        Disconnect
                                    </button>
                                </div>
                            )}
                        </div>
                    ) : (
                        <button
                            onClick={() => {
                                const argent = connectors.find(c => c.id === "argentX");
                                if (argent) connect({ connector: argent });
                            }}
                            className="btn-primary text-xs sm:text-sm px-4 sm:px-6 py-2"
                        >
                            Connect
                        </button>
                    )}

                    {/* Mobile Hamburger */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 text-muted hover:text-white"
                        aria-label="Toggle menu"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            {mobileMenuOpen ? (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            ) : (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            )}
                        </svg>
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
                <div className="md:hidden absolute top-full left-0 right-0 bg-[#0a0a0a] border-b border-[#2a2a2a] z-50">
                    <nav className="flex flex-col py-4">
                        {navItems.map((item) => {
                            const isActive = pathname === item.href ||
                                (item.href === "/" && pathname === "/vault");
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    onClick={() => setMobileMenuOpen(false)}
                                    className={`px-6 py-3 text-sm font-ui transition-colors ${isActive
                                        ? "text-highlight bg-highlight/10"
                                        : "text-muted hover:text-white hover:bg-[#1a1a1a]"
                                        }`}
                                >
                                    {item.name}
                                </Link>
                            );
                        })}
                    </nav>
                </div>
            )}
        </header>
    );
}
