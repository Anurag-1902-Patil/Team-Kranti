import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SIH26122 — Team Kranti | Intelligent Data Capture & Schedule-Linking Layer",
  description:
    "Smart India Hackathon 2026 — AI-powered progress report ingestion, automatic matching to Primavera P6 plan activities, and human-in-the-loop review for Oil India infrastructure projects.",
  keywords: ["SIH", "Smart India Hackathon", "Oil India", "Primavera P6", "construction", "infrastructure"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
