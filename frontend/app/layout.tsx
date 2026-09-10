import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

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
  title: "Kranti P1 — Oil India Project Controls",
  description:
    "Intelligent Data Capture & Schedule-Linking Layer for Oil India Limited — Smart India Hackathon 2026 SIH26122.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}
        style={{
          fontFamily: "var(--font-ibm-plex-sans), 'IBM Plex Sans', Arial, sans-serif",
          background: "var(--bg)",
          color: "var(--ink)",
          margin: 0,
          padding: 0,
          height: "100vh",
          overflow: "hidden",
        }}
      >
        {children}
      </body>
    </html>
  );
}
