import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import NLSearchBar from "@/components/NLSearchBar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Team Kranti — Oil India Infrastructure Project Controls",
  description:
    "Intelligent Data Capture & Schedule-Linking Layer for Oil India Limited — Smart India Hackathon 2026 SIH26122.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 min-h-screen antialiased`}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Top Engineering Bar */}
            <header className="h-14 px-6 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-sm flex items-center justify-between gap-4 z-40">
              <div className="flex-1 max-w-xl">
                <NLSearchBar />
              </div>
              <div className="flex items-center gap-3">
                <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  XER Engine: Active
                </span>
                <span className="text-[11px] font-mono text-cyan-400/90 px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/50">
                  Project: OIL-EXP-2026
                </span>
              </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto bg-[#080c14]">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
