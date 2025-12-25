"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface Toast {
    id: string;
    type: "success" | "error" | "info" | "loading";
    title: string;
    message?: string;
    txHash?: string;
}

interface ToastContextType {
    showToast: (toast: Omit<Toast, "id">) => string;
    hideToast: (id: string) => void;
    updateToast: (id: string, updates: Partial<Omit<Toast, "id">>) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within a ToastProvider");
    }
    return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const showToast = useCallback((toast: Omit<Toast, "id">) => {
        const id = Math.random().toString(36).slice(2);
        setToasts((prev) => [...prev, { ...toast, id }]);

        // Auto-hide after 5s for success/error/info, not for loading
        if (toast.type !== "loading") {
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, 5000);
        }

        return id;
    }, []);

    const hideToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const updateToast = useCallback((id: string, updates: Partial<Omit<Toast, "id">>) => {
        setToasts((prev) =>
            prev.map((t) => (t.id === id ? { ...t, ...updates } : t))
        );

        // If updating to success/error, auto-hide after 5s
        if (updates.type && updates.type !== "loading") {
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, 5000);
        }
    }, []);

    return (
        <ToastContext.Provider value={{ showToast, hideToast, updateToast }}>
            {children}

            {/* Toast Container */}
            <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 max-w-sm">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={`
                            px-5 py-4 rounded-xl border shadow-2xl backdrop-blur-sm
                            ${toast.type === "success" ? "bg-[#1a2a1a] border-green-500/40" : ""}
                            ${toast.type === "error" ? "bg-[#2a1a1a] border-red-500/40" : ""}
                            ${toast.type === "info" ? "bg-[#1a1a2a] border-blue-500/40" : ""}
                            ${toast.type === "loading" ? "bg-[#1a1a1a] border-highlight/40" : ""}
                        `}
                        style={{ animation: "slideIn 0.3s ease-out" }}
                    >
                        <div className="flex items-start gap-3">
                            {/* Icon */}
                            <div className="flex-shrink-0 mt-0.5">
                                {toast.type === "success" && (
                                    <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                )}
                                {toast.type === "error" && (
                                    <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                )}
                                {toast.type === "info" && (
                                    <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                )}
                                {toast.type === "loading" && (
                                    <div className="w-5 h-5 border-2 border-highlight border-t-transparent rounded-full animate-spin" />
                                )}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium ${toast.type === "success" ? "text-green-400" :
                                        toast.type === "error" ? "text-red-400" :
                                            toast.type === "info" ? "text-blue-400" :
                                                "text-white"
                                    }`}>
                                    {toast.title}
                                </p>
                                {toast.message && (
                                    <p className="text-xs text-muted mt-1">{toast.message}</p>
                                )}
                                {toast.txHash && (
                                    <a
                                        href={`https://voyager.online/tx/${toast.txHash}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-highlight hover:underline mt-1 inline-block"
                                    >
                                        View on Voyager →
                                    </a>
                                )}
                            </div>

                            {/* Close button */}
                            <button
                                onClick={() => hideToast(toast.id)}
                                className="flex-shrink-0 text-muted hover:text-white transition-colors"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Animation keyframes */}
            <style jsx global>{`
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateX(100%);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
            `}</style>
        </ToastContext.Provider>
    );
}
