"use client";

import Link from "next/link";

export function Footer() {
    return (
        <footer className="py-6 mt-auto border-t border-[#2a2a2a]">
            <div className="max-w-6xl mx-auto px-6 flex items-center justify-center gap-8">
                <Link
                    href="https://x.com/unboundedapp"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted hover:text-white transition-colors text-sm flex items-center gap-2"
                >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                    </svg>
                    X
                </Link>
                <Link
                    href="https://docs.unboundfi.xyz/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted hover:text-white transition-colors text-sm flex items-center gap-2"
                >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Docs
                </Link>
            </div>
        </footer>
    );
}
