"use client";

import Button from "@/components/Button";
import ErrorBanner from "@/components/ErrorBanner";
import type { ServiceRow } from "@/lib/api";

interface TiersScreenProps {
  services: ServiceRow[];
  tiers: Record<string, 1 | 2 | 3>;
  setTier: (serviceName: string, tier: 1 | 2 | 3) => void;
  onBack: () => void;
  onRun: () => void;
  loading: boolean;
  error: string | null;
}

export default function TiersScreen({ services, tiers, setTier, onBack, onRun, loading, error }: TiersScreenProps) {
  const tier1Count = Object.values(tiers).filter((t) => t === 1).length;

  return (
    <div className="screen-enter d-screen" style={{ maxWidth: 900 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 className="d-h1">Declare service tiers</h1>
        <p style={{ marginTop: 8, fontSize: 15, color: "var(--text-muted)", maxWidth: 600 }}>
          Mark services as essential. Tier 1 = never touched. Tier 2 = flagged if touched. Tier 3 = flexible.
        </p>
      </div>

      <div className="d-tiers-table">
        <div className="d-tiers-head-row">
          <span>SERVICE</span>
          <span style={{ textAlign: "right" }}>COST / MO</span>
          <span style={{ textAlign: "center" }}>ITEMS</span>
          <span style={{ textAlign: "center" }}>TIER</span>
        </div>
        {services.map((svc) => {
          const t = tiers[svc.service_name] ?? svc.default_tier;
          return (
            <div className="d-tiers-row" key={svc.service_name}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-700)" }}>{svc.service_name}</div>
              </div>
              <div style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink-700)" }}>
                ${svc.total_cost_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-muted)" }}>
                {svc.line_item_count}
              </div>
              <div style={{ display: "flex", gap: 4, justifyContent: "center" }}>
                <button className="tier-btn tier-1" data-active={t === 1} onClick={() => setTier(svc.service_name, 1)}>1</button>
                <button className="tier-btn tier-2" data-active={t === 2} onClick={() => setTier(svc.service_name, 2)}>2</button>
                <button className="tier-btn tier-3" data-active={t === 3} onClick={() => setTier(svc.service_name, 3)}>3</button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="d-warn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#dc4a3f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span style={{ fontSize: 13, color: "#a23c34" }}>
          <strong>{tier1Count}</strong> service(s) marked tier 1 — these will be excluded from all recommendations.
        </span>
      </div>

      {error && (
        <div style={{ marginTop: 16 }}>
          <ErrorBanner message={error} />
        </div>
      )}

      <div style={{ marginTop: 24, display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <Button variant="cream" onClick={onBack}>← Back</Button>
        <Button variant="dark" onClick={onRun} disabled={loading}>
          {loading ? "Starting…" : "Run analysis →"}
        </Button>
      </div>
    </div>
  );
}
