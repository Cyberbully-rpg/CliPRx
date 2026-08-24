import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "CliPRx — Ranked cloud cost fixes from a billing CSV",
  description: "Upload a CSV. Get ranked, risk-scored cost fixes as sprint tickets.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          background: "var(--bg-page)",
          color: "var(--text-body)",
          fontFamily: "var(--font-sans)",
          WebkitFontSmoothing: "antialiased",
          textRendering: "optimizeLegibility",
        }}
      >
        {children}
      </body>
    </html>
  );
}
