"use client";

import Button from "@/components/Button";
import ErrorBanner from "@/components/ErrorBanner";
import type { Prescription, ReportDetail } from "@/lib/api";

interface DetailScreenProps {
  report: ReportDetail | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onDownloadPdf: () => void;
  onDelete: () => void;
  pdfLoading: boolean;
  deleteLoading: boolean;
}

const RISK_BADGE: Record<string, { bg: string; text: string }> = {
  Low: { bg: "rgba(63,184,127,.12)", text: "#2f7d59" },
  Medium: { bg: "rgba(233,162,59,.14)", text: "#8a5a12" },
  High: { bg: "rgba(226,84,74,.12)", text: "#a23c34" },
};

function formatMoney(n: number): string {
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function daysUntil(iso: string): number {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / (1000 * 60 * 60 * 24)));
}

function PrescriptionCard({ rx, index }: { rx: Prescription; index: number }) {
  const badge = RISK_BADGE[rx.risk_level] ?? RISK_BADGE.Low;
  return (
    <article className="rx-card" style={rx.is_conflicted ? { borderColor: "rgba(226,84,74,.28)" } : undefined}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-subtle)" }}>#{index + 1}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 15, fontWeight: 500, color: "var(--ink-700)" }}>{rx.service_name}</span>
        <span style={{ fontSize: 12, fontWeight: 600, padding: "3px 9px", borderRadius: 6, background: badge.bg, color: badge.text }}>
          {rx.risk_level} risk
        </span>
        {rx.is_conflicted && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 600, padding: "3px 9px", borderRadius: 6, background: "rgba(226,84,74,.08)", border: "1px solid rgba(226,84,74,.2)", color: "#a23c34" }}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#e2544a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            conflict · tier-{rx.tier}
          </span>
        )}
        <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500, color: rx.is_conflicted ? "var(--text-muted)" : "#2f7d59" }}>
          {formatMoney(rx.savings_min)}–{formatMoney(rx.savings_max)}/mo
        </span>
      </div>
      <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--text-body)", maxWidth: 720, marginBottom: 12 }}>
        {rx.recommended_action}
      </p>
      {rx.is_conflicted && rx.conflict_reason && (
        <p style={{ fontSize: 13, lineHeight: 1.5, color: "#a23c34", marginBottom: 12 }}>{rx.conflict_reason}</p>
      )}
      <div style={{ display: "flex", gap: 20, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", flexWrap: "wrap" }}>
        <span>effort {rx.engineering_hours} eng-hrs</span>
        <span>anomaly {rx.anomaly_score.toFixed(2)}</span>
        <span style={rx.is_conflicted ? { color: "#a23c34" } : undefined}>
          {rx.is_conflicted ? "excluded from ranking" : `ROI rank ${rx.rank_position}`}
        </span>
        <span>tier {rx.tier}</span>
      </div>
    </article>
  );
}

export default function DetailScreen({ report, loading, error, onBack, onDownloadPdf, onDelete, pdfLoading, deleteLoading }: DetailScreenProps) {
  return (
    <div className="screen-enter d-screen" style={{ maxWidth: 960 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <button onClick={onBack} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 13, fontFamily: "var(--font-sans)", display: "flex", alignItems: "center", gap: 4 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Reports
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && <p style={{ fontSize: 14, color: "var(--text-muted)" }}>Loading…</p>}

      {report && (
        <>
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 20, marginBottom: 36, paddingBottom: 24, borderBottom: "1px solid var(--border-hairline)" }}>
            <div>
              <h1 style={{ fontFamily: "var(--font-serif-display)", fontSize: 32, fontWeight: 400, color: "var(--text-heading)" }}>Report detail</h1>
              <div style={{ display: "flex", gap: 16, marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 13, flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-muted)" }}>{formatDate(report.created_at)}</span>
                {report.total_savings_min != null && report.total_savings_max != null && (
                  <span style={{ color: "#2f7d59" }}>
                    {formatMoney(report.total_savings_min)}–{formatMoney(report.total_savings_max)} /mo
                  </span>
                )}
                <span style={{ color: "var(--text-muted)" }}>{report.prescription_count ?? report.prescriptions.length} prescriptions</span>
                {!!report.conflict_count && <span style={{ color: "#a23c34" }}>{report.conflict_count} conflict(s)</span>}
              </div>
            </div>
            <Button variant="cream" onClick={onDownloadPdf} disabled={pdfLoading}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                {pdfLoading ? "Preparing…" : "Download PDF"}
              </span>
            </Button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {report.prescriptions.map((rx, i) => (
              <PrescriptionCard rx={rx} index={i} key={rx.id} />
            ))}
            {report.prescriptions.length === 0 && (
              <p style={{ fontSize: 14, color: "var(--text-muted)" }}>No anomalies found requiring action.</p>
            )}
          </div>

          <div style={{ marginTop: 28, padding: "16px 20px", background: "var(--surface-sunken)", border: "1px solid var(--border-hairline)", borderRadius: "var(--radius-sm)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              {report.expires_at && (
                <>Report expires in <strong style={{ color: "var(--ink-700)" }}>{daysUntil(report.expires_at)} days</strong> · </>
              )}
              Soft-delete available anytime
            </div>
            <button
              onClick={onDelete}
              disabled={deleteLoading}
              style={{ background: "none", border: "1px solid rgba(226,84,74,.3)", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, color: "#a23c34", cursor: "pointer", fontFamily: "var(--font-sans)" }}
            >
              {deleteLoading ? "Deleting…" : "Delete report"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
