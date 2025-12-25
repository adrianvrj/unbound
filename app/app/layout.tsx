import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { StarknetProvider } from "@/providers/starknet";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ToastProvider } from "@/components/Toast";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
});

export const metadata: Metadata = {
  title: "Unbound - Leveraged wBTC Vault",
  description: "Earn leveraged yields on your wBTC with Vesu",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geist.variable} antialiased`}>
        <StarknetProvider>
          <ToastProvider>
            <div className="min-h-screen">
              <Header />
              <main className="max-w-6xl mx-auto px-4 sm:px-8 py-6 sm:py-10 min-h-screen">
                {children}
              </main>
              <Footer />
            </div>
          </ToastProvider>
        </StarknetProvider>
      </body>
    </html>
  );
}

