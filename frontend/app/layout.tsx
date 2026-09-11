import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { AppProvider } from "@/lib/AppContext";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { CommandPalette } from "@/components/CommandPalette";
import { ActivityDetailDrawer } from "@/components/ActivityDetailDrawer";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-plex-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kranti P6 — Project Controls & Schedule Integration",
  description:
    "Intelligent Data Capture & Schedule-Linking Layer for Oil India Limited — Smart India Hackathon 2026 SIH26122.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${ibmPlexSans.variable} ${ibmPlexMono.variable} antialiased bg-[#FAFAFA] text-slate-900`}>
        <AppProvider>
          <div className="flex flex-col h-screen overflow-hidden">
            <Header />
            <div className="flex flex-1 overflow-hidden">
              <Sidebar />
              <main className="flex-1 overflow-y-auto bg-[#FAFAFA]">
                {children}
              </main>
            </div>
            <CommandPalette />
            <ActivityDetailDrawer />
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
