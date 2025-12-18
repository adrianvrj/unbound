"use client";

import Image from "next/image";
import { useState, useEffect } from "react";

export default function Home() {
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        // Check system preference on mount
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setIsDark(true);
        }
    }, []);

    return (
        <div className={`relative min-h-screen w-full overflow-hidden transition-colors duration-300 ${isDark ? 'bg-black' : 'bg-white'}`}>
            {/* Background Image */}
            <div
                className="absolute inset-0 z-0 transition-opacity duration-300"
                style={{
                    backgroundImage: `url(${isDark ? '/bg-dark.png' : '/bg.png'})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat',
                }}
            />

            {/* Content */}
            <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-6">
                {/* Logo - Top Left */}
                <div className="absolute top-6 left-6 ml-10 mt-5">
                    <Image
                        src="/logo.png"
                        alt="Unbound"
                        width={50}
                        height={50}
                        priority
                    />
                </div>

                {/* Dark Mode Toggle - Top Right */}
                <button
                    onClick={() => setIsDark(!isDark)}
                    className={`cursor-pointer absolute top-6 right-6 mr-10 mt-5 p-2 rounded-full transition-colors ${isDark ? 'bg-white text-black' : 'bg-black text-white'
                        }`}
                    aria-label="Toggle dark mode"
                >
                    {isDark ? (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                        </svg>
                    ) : (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                        </svg>
                    )}
                </button>

                {/* Title */}
                <h1 className={`mb-20 text-center text-4xl font-medium md:text-4xl lg:text-5xl transition-colors ${isDark ? 'text-white' : 'text-black'}`}>
                    Unleash Your Yield
                </h1>

                {/* Subtitle */}
                <p className={`mb-20 text-center text-lg md:text-xl transition-colors ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    One Click. Maximum Leverage. Zero Hassle
                </p>

                {/* Buttons */}
                <div className="flex gap-4">
                    <a
                        href="#"
                        className={`rounded-full px-8 py-3 text-base font-medium transition-all hover:opacity-80 ${isDark ? 'bg-white text-black' : 'bg-black text-white'
                            }`}
                    >
                        try now
                    </a>
                    <a
                        href="#"
                        className={`rounded-full px-8 py-3 text-base font-medium transition-all hover:opacity-80 ${isDark ? 'bg-white text-black' : 'bg-black text-white'
                            }`}
                    >
                        docs
                    </a>
                </div>
            </div>
        </div>
    );
}
