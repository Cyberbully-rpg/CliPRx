"use client";

import Link from "next/link";

type Screen = "upload" | "tiers" | "pipeline" | "reports" | "detail";

interface SidebarProps {
  screen: Screen;
  goUpload: () => void;
  goReports: () => void;
}

export default function Sidebar({ screen, goUpload, goReports }: SidebarProps) {
  const isUpload = screen === "upload" || screen === "tiers" || screen === "pipeline";
  const isReports = screen === "reports" || screen === "detail";

  return (
    <aside className="d-sidebar">
      <Link href="/" className="d-sidebar-logo">
        <span style={{ width: 8, height: 8, borderRadius: 2, background: "var(--signal-running)" }} />
        CliPRx
      </Link>
      <Link href="/" className="sidebar-link d-sidebar-back">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        Back to homepage
      </Link>
      <button className="sidebar-link" data-active={isUpload} onClick={goUpload}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        Upload CSV
      </button>
      <button className="sidebar-link" data-active={isReports} onClick={goReports}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        Reports
      </button>
      <div style={{ flex: 1 }} />
      <div className="d-sidebar-foot">
        <div style={{ fontSize: 11, color: "var(--text-subtle)" }}>Single-tenant · SOC 2</div>
      </div>
    </aside>
  );
}
