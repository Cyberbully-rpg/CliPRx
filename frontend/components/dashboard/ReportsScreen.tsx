"use client";

import Button from "@/components/Button";
import ErrorBanner from "@/components/ErrorBanner";
import type { ReportSummary } from "@/lib/api";

interface ReportsScreenProps {
  reports: ReportSummary[];
  loading: boolean;
  error: string | null;
  onOpen: (reportId: string) => void;
  onNew: () => void;
}

const STATUS_STYLES: Record<string, { dot: string; bg: string; text: string }> = {
  complete: { dot: "#3fb87f", bg: "rgba(63,184,127,.1)", text: "#2f7d59" },
  running: { dot: "var(--signal-running)", bg: "rgba(52,211,153,.1)", text: "#2f7d59" },
  pending: { dot: "var(--text-subtle)", bg: "var(--surface-sunken)", text: "var(--text-subtle)" },
  failed: { dot: "#dc4a3f", bg: "rgba(226,84,74,.1)", text: "#a23c34" },
};

function formatSavings(min: number | null, max: number | null): string {
  if (min == null || max == null) return "—";
  return `$${min.toLocaleString(undefined, { maximumFractionDigits: 0 })}–${max.toLocaleString(undefined, { maximumFractionDigits: 0 })}/mo`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function ReportsScreen({ reports, loading, error, onOpen, onNew }: ReportsScreenProps) {
  return (
    <div className="screen-enter d-screen" style={{ maxWidth: 900 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <h1 className="d-h1">Reports</h1>
          <p style={{ marginTop: 6, fontSize: 14, color: "var(--text-muted)" }}>
            {reports.length} report(s) · 30-day retention
          </p>
        </div>
        <Button variant="dark" onClick={onNew}>+ New analysis</Button>
      </div>

      {error && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner message={error} />
        </div>
      )}

      {loading && <p style={{ fontSize: 14, color: "var(--text-muted)" }}>Loading…</p>}

      {!loading && reports.length === 0 && !error && (
        <p style={{ fontSize: 14, color: "var(--text-muted)" }}>No reports yet. Run an analysis to get started.</p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {reports.map((rpt) => {
          const status = STATUS_STYLES[rpt.status] ?? STATUS_STYLES.pending;
          return (
            <div className="rx-card" style={{ cursor: "pointer" }} key={rpt.id} onClick={() => onOpen(rpt.id)}>
              <div className="d-report-card-head">
                <span className="d-status-dot" style={{ background: status.dot }} />
                <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>{formatDate(rpt.created_at)}</span>
                <span className="d-status-pill" style={{ marginLeft: "auto", background: status.bg, color: status.text }}>
                  {rpt.status}
                </span>
              </div>
              <div style={{ display: "flex", gap: 24, fontFamily: "var(--font-mono)", fontSize: 13 }}>
                <span style={{ color: "#2f7d59" }}>{formatSavings(rpt.total_savings_min, rpt.total_savings_max)}</span>
                <span style={{ color: "var(--text-muted)" }}>{rpt.prescription_count ?? "—"} prescriptions</span>
                {!!rpt.conflict_count && <span style={{ color: "#a23c34" }}>{rpt.conflict_count} conflict(s)</span>}
              </div>
              {rpt.expires_at && (
                <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-subtle)" }}>
                  Expires {formatDate(rpt.expires_at)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
